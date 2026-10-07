"""SCHEDULER MICROBENCHMARK

Isolated scheduling policy microbenchmark comparing algorithm decision latency,
throughput, and work allocation across simulated heterogeneous nodes.

Compares:
1. Round Robin
2. Least Loaded
3. Highest Bid
4. TaskMesh Adaptive (EWMA + DRR + MWU + Q-learning)
"""

import asyncio
import json
import time
from typing import Any, Dict, List

from taskmesh.core.enums import NodeStatus, SchedulerMode
from taskmesh.core.models import (
    NodeCapabilities,
    NodeProfile,
    NodeTelemetry,
    Task,
)
from taskmesh.fairness.drr import calculate_fairness_cv
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.baseline import (
    HighestBidScheduler,
    LeastLoadedScheduler,
    RoundRobinScheduler,
)


def create_heterogeneous_cluster() -> List[NodeProfile]:
    """Creates a realistic 4-node heterogeneous cluster."""
    # Node 1: High-end GPU workstation
    n1 = NodeProfile(
        id="node-gpu-rig",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=16,
            cpu_frequency_mhz=3800.0,
            ram_total_mb=32768,
            ram_available_mb=28000,
            has_gpu=True,
            gpu_name="NVIDIA RTX 4090",
            supported_handlers=["log", "cpu_test", "image_inference"],
            tags=["gpu", "cuda", "fast"],
        ),
        telemetry=NodeTelemetry(node_id="node-gpu-rig", cpu_percent=15.0, ram_percent=25.0, network_latency_ms=1.2),
        base_score=2.8,
    )

    # Node 2: Fast multi-core CPU server
    n2 = NodeProfile(
        id="node-cpu-server",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=12,
            cpu_frequency_mhz=3200.0,
            ram_total_mb=16384,
            ram_available_mb=12000,
            has_gpu=False,
            supported_handlers=["log", "cpu_test"],
            tags=["cpu", "fast"],
        ),
        telemetry=NodeTelemetry(node_id="node-cpu-server", cpu_percent=20.0, ram_percent=35.0, network_latency_ms=2.0),
        base_score=1.8,
    )

    # Node 3: Standard office laptop
    n3 = NodeProfile(
        id="node-laptop",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=4,
            cpu_frequency_mhz=2400.0,
            ram_total_mb=8192,
            ram_available_mb=4096,
            has_gpu=False,
            supported_handlers=["log", "cpu_test"],
            tags=["cpu", "general"],
        ),
        telemetry=NodeTelemetry(node_id="node-laptop", cpu_percent=45.0, ram_percent=60.0, network_latency_ms=5.0),
        base_score=1.0,
    )

    # Node 4: Edge mini PC
    n4 = NodeProfile(
        id="node-edge-mini",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=2,
            cpu_frequency_mhz=1800.0,
            ram_total_mb=4096,
            ram_available_mb=2048,
            has_gpu=False,
            supported_handlers=["log", "cpu_test"],
            tags=["cpu", "low-power"],
        ),
        telemetry=NodeTelemetry(node_id="node-edge-mini", cpu_percent=60.0, ram_percent=70.0, network_latency_ms=8.5),
        base_score=0.6,
    )

    return [n1, n2, n3, n4]


async def run_benchmark_for_scheduler(scheduler_name: str, scheduler_instance: Any, tasks: List[Task]) -> Dict[str, Any]:
    nodes = create_heterogeneous_cluster()
    node_map = {n.id: n for n in nodes}
    allocation_counts: Dict[str, int] = {n.id: 0 for n in nodes}

    latencies_ms: List[float] = []
    start_total = time.perf_counter()

    for task in tasks:
        t0 = time.perf_counter()
        decision = await scheduler_instance.select_node(task, nodes)
        dt = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt)

        selected_id = decision.selected_node_id
        allocation_counts[selected_id] += 1
        node = node_map[selected_id]
        node.total_completed += 1

        # Simulate dynamic outcome feedback for adaptive scheduler
        if isinstance(scheduler_instance, AdaptiveScheduler):
            exec_time = 0.05 / max(0.5, node.base_score)
            await scheduler_instance.record_task_outcome(
                node=node,
                task=task,
                decision=decision,
                actual_duration_seconds=exec_time,
                success=True,
            )

    total_time = time.perf_counter() - start_total
    throughput = len(tasks) / max(0.001, total_time)

    counts = list(allocation_counts.values())
    fairness_cv = calculate_fairness_cv(counts)

    return {
        "scheduler": scheduler_name,
        "total_tasks": len(tasks),
        "total_time_seconds": round(total_time, 4),
        "throughput_tasks_per_sec": round(throughput, 1),
        "avg_scheduling_latency_ms": round(sum(latencies_ms) / len(latencies_ms), 3),
        "max_scheduling_latency_ms": round(max(latencies_ms), 3),
        "fairness_cv": fairness_cv,
        "allocations_per_node": allocation_counts,
    }


async def main() -> None:
    print("=" * 70)
    print("TaskMesh Scheduler Evaluation Benchmark Suite")
    print("Heterogeneous Cluster: 4 Nodes (GPU Rig, CPU Server, Laptop, Edge Mini)")
    print("Workload: 200 Mixed Generic Tasks (priorities 0-20, mixed requirements)")
    print("=" * 70)

    # Generate benchmark workload
    workload: List[Task] = []
    for i in range(200):
        prio = (i * 7) % 25
        workload.append(Task(id=f"bench_task_{i}", task_type="cpu_test", priority=prio))

    schedulers = [
        ("Round Robin", RoundRobinScheduler()),
        ("Least Loaded", LeastLoadedScheduler()),
        ("Highest Bid", HighestBidScheduler()),
        ("TaskMesh Adaptive", AdaptiveScheduler(ewma_alpha=0.2, mwu_eta=0.1, rl_lr=0.1)),
    ]

    all_results = []
    for name, sched in schedulers:
        res = await run_benchmark_for_scheduler(name, sched, workload)
        all_results.append(res)
        print(f"\n--- {name} ---")
        print(f"  Throughput: {res['throughput_tasks_per_sec']} tasks/sec")
        print(f"  Avg Latency: {res['avg_scheduling_latency_ms']} ms")
        print(f"  Fairness (CV): {res['fairness_cv']} (lower = more balanced)")
        print(f"  Node Distribution: {res['allocations_per_node']}")

    with open("benchmarks/results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\nResults successfully saved to benchmarks/results.json")


if __name__ == "__main__":
    asyncio.run(main())
