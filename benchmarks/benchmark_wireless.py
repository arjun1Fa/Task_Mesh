"""TASKMESH WIRELESS INFERENCE BENCHMARK FRAMEWORK

Prepares benchmark tooling to measure and compare:
1. Local execution: T_local = local inference time
2. Wireless offloading: T_remote = upload_transfer + network_rtt + remote_queue + remote_inference + download_transfer
3. Schedulers under simulated/measured Wi-Fi network profiles:
   - Local-only baseline
   - Round Robin
   - Least Loaded
   - Highest Bid
   - TaskMesh Adaptive (Network-aware cost estimator + EWMA + DRR + MWU)
4. Payload size variations (e.g. 50KB, 500KB, 2MB, 5MB frames)
"""

import argparse
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from taskmesh.core.enums import NodeStatus, OffloadPolicy, SchedulerMode
from taskmesh.core.models import (
    BinaryPayloadMeta,
    NodeCapabilities,
    NodeProfile,
    NodeTelemetry,
    Task,
)
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.baseline import (
    HighestBidScheduler,
    LeastLoadedScheduler,
    RoundRobinScheduler,
)
from taskmesh.wireless.estimator import NetworkEstimator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_wireless")


class WirelessBenchmarkRunner:
    """Benchmark suite for local vs wireless inference offloading."""

    def __init__(self) -> None:
        self.estimator = NetworkEstimator()

    def build_test_nodes(self) -> List[NodeProfile]:
        """Creates a realistic mixed edge/wireless setup.

        - local-laptop: CPU-only, local edge device where task originates.
        - wifi-gpu-rig: Powerful remote GPU workstation over Wi-Fi.
        - wifi-edge-pi: Lightweight remote edge device over Wi-Fi.
        """
        local_node = NodeProfile(
            id="local-laptop",
            status=NodeStatus.ONLINE,
            is_local=True,
            lan_ip="192.168.1.10",
            capabilities=NodeCapabilities(
                cpu_cores=4,
                cpu_frequency_mhz=2200.0,
                ram_total_mb=8192,
                ram_available_mb=4096,
                has_gpu=False,
                is_local=True,
                supported_handlers=["image_inference", "log"],
                tags=["client", "local", "cpu"],
            ),
            telemetry=NodeTelemetry(
                node_id="local-laptop",
                cpu_percent=55.0,
                ram_percent=60.0,
                network_latency_ms=0.5,
                rtt_ewma_ms=0.5,
                upload_mbps_ewma=1000.0,
                download_mbps_ewma=1000.0,
            ),
            base_score=1.0,
        )

        gpu_node = NodeProfile(
            id="wifi-gpu-rig",
            status=NodeStatus.ONLINE,
            is_local=False,
            lan_ip="192.168.1.50",
            capabilities=NodeCapabilities(
                cpu_cores=16,
                cpu_frequency_mhz=3800.0,
                ram_total_mb=32768,
                ram_available_mb=26000,
                has_gpu=True,
                gpu_name="NVIDIA RTX 4080",
                gpu_vram_mb=16384,
                supported_handlers=["image_inference", "log"],
                tags=["gpu", "cuda", "wifi-remote"],
            ),
            telemetry=NodeTelemetry(
                node_id="wifi-gpu-rig",
                cpu_percent=12.0,
                ram_percent=20.0,
                network_latency_ms=18.5,
                rtt_ewma_ms=18.5,
                upload_mbps_ewma=45.0,
                download_mbps_ewma=60.0,
            ),
            base_score=3.5,
        )

        pi_node = NodeProfile(
            id="wifi-edge-pi",
            status=NodeStatus.ONLINE,
            is_local=False,
            lan_ip="192.168.1.75",
            capabilities=NodeCapabilities(
                cpu_cores=4,
                cpu_frequency_mhz=1500.0,
                ram_total_mb=4096,
                ram_available_mb=2048,
                has_gpu=False,
                supported_handlers=["image_inference", "log"],
                tags=["edge", "wifi-remote"],
            ),
            telemetry=NodeTelemetry(
                node_id="wifi-edge-pi",
                cpu_percent=70.0,
                ram_percent=75.0,
                network_latency_ms=28.0,
                rtt_ewma_ms=28.0,
                upload_mbps_ewma=20.0,
                download_mbps_ewma=25.0,
            ),
            base_score=0.8,
        )

        return [local_node, gpu_node, pi_node]

    async def run_cost_comparison(self, payload_sizes_kb: List[int]) -> Dict[str, Any]:
        """Evaluates theoretical and estimated cost models across varying image payload sizes."""
        nodes = self.build_test_nodes()
        results: Dict[str, Any] = {}

        for size_kb in payload_sizes_kb:
            payload_bytes = size_kb * 1024
            tid = f"bench-task-{size_kb}k"
            meta = BinaryPayloadMeta(
                task_id=tid,
                size_bytes=payload_bytes,
                mime_type="image/jpeg",
                checksum_sha256="test",
            )
            task = Task(
                id=tid,
                task_type="image_inference",
                offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
                binary_meta=meta,
            )

            comparison = self.estimator.compare_local_vs_remote(
                task,
                local_node=nodes[0],
                remote_node=nodes[1],
                payload_size_bytes=payload_bytes,
            )
            rem_details = comparison["remote_details"]
            results[f"{size_kb}KB"] = {
                "payload_size_kb": size_kb,
                "local_estimate_ms": round(comparison["local_estimate_ms"], 2) if comparison["local_estimate_ms"] else -1,
                "remote_estimate_ms": round(comparison["remote_estimate_ms"], 2),
                "upload_ms": round(rem_details["upload_ms"], 2),
                "remote_inference_ms": round(rem_details["remote_inference_ms"], 2),
                "download_ms": round(rem_details["download_ms"], 2),
                "offload_decision": comparison["decision"],
                "offload_reason": comparison["reason"],
                "fastest_node": nodes[1].id if comparison["decision"] == "remote" else nodes[0].id,
            }

        return results

    async def run_scheduler_comparison(self, num_tasks: int = 50) -> Dict[str, Any]:
        """Benchmarks scheduling decisions across the 4 scheduler algorithms with wireless-aware telemetry."""
        nodes = self.build_test_nodes()
        schedulers = {
            "round_robin": RoundRobinScheduler(),
            "least_loaded": LeastLoadedScheduler(),
            "highest_bid": HighestBidScheduler(),
            "taskmesh_adaptive": AdaptiveScheduler(),
        }

        comparison_results: Dict[str, Any] = {}

        for name, sched in schedulers.items():
            start_t = time.perf_counter()
            decisions = []
            offload_counts = {"local": 0, "remote": 0}
            node_counts: Dict[str, int] = {}

            for i in range(num_tasks):
                # Varied sizes: 100KB, 500KB, 1.5MB
                size_kb = [100, 500, 1500][i % 3]
                tid = f"bench-{name}-{i}"
                meta = BinaryPayloadMeta(
                    task_id=tid,
                    size_bytes=size_kb * 1024,
                    mime_type="image/jpeg",
                    checksum_sha256="bench",
                )
                task = Task(
                    id=tid,
                    task_type="image_inference",
                    offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
                    binary_meta=meta,
                )

                decision = await sched.select_node(task, nodes)
                if decision:
                    decisions.append(decision)
                    nid = decision.selected_node_id
                    node_counts[nid] = node_counts.get(nid, 0) + 1
                    if decision.offload_decision == "remote":
                        offload_counts["remote"] += 1
                    else:
                        offload_counts["local"] += 1

            duration_ms = (time.perf_counter() - start_t) * 1000
            avg_decision_latency_ms = duration_ms / num_tasks if num_tasks > 0 else 0

            comparison_results[name] = {
                "tasks_scheduled": len(decisions),
                "total_time_ms": round(duration_ms, 2),
                "avg_decision_latency_ms": round(avg_decision_latency_ms, 4),
                "node_distribution": node_counts,
                "offload_decisions": offload_counts,
            }

        return comparison_results


async def main() -> None:
    parser = argparse.ArgumentParser(description="TaskMesh Wireless Inference Benchmark")
    parser.add_argument("--tasks", type=int, default=50, help="Number of simulated tasks for scheduler comparison")
    parser.add_argument("--output", type=str, default="wireless_benchmark_results.json", help="Path to output JSON")
    args = parser.parse_args()

    runner = WirelessBenchmarkRunner()

    logger.info("Starting Wireless Offloading Cost Comparison...")
    sizes = [50, 200, 500, 1000, 2048, 5120]  # 50KB to 5MB
    cost_results = await runner.run_cost_comparison(sizes)

    logger.info("Running Scheduler Decision Comparison on Wireless Workloads...")
    sched_results = await runner.run_scheduler_comparison(args.tasks)

    summary = {
        "benchmark": "TaskMesh Wireless Offloading Cost & Schedulers",
        "timestamp": time.time(),
        "payload_size_cost_matrix": cost_results,
        "scheduler_comparison": sched_results,
    }

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Wireless benchmark completed. Results saved to {args.output}")
    print("\n=== PAYLOAD SIZE COST ESTIMATION SUMMARY ===")
    print(f"{'Size (KB)':<12} | {'Local (ms)':<12} | {'Remote (ms)':<12} | {'Upload (ms)':<12} | {'Decision':<10} | {'Node':<15}")
    print("-" * 75)
    for k, v in cost_results.items():
        print(f"{v['payload_size_kb']:<12} | {v['local_estimate_ms']:<12} | {v['remote_estimate_ms']:<12} | {v['upload_ms']:<12} | {v['offload_decision']:<10} | {v['fastest_node']:<15}")

    print("\n=== SCHEDULER DISTRIBUTION SUMMARY ===")
    for s_name, s_data in sched_results.items():
        print(f"[{s_name.upper()}] Avg Latency: {s_data['avg_decision_latency_ms']}ms | Distribution: {s_data['node_distribution']} | Offloads: {s_data['offload_decisions']}")


if __name__ == "__main__":
    asyncio.run(main())
