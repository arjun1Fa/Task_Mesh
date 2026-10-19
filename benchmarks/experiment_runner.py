"""TASKMESH ADVANCED SCHEDULER EXPERIMENTATION AND EVALUATION FRAMEWORK

Provides reproducible, statistical microbenchmarks, network-condition simulations,
scheduler ablations, and localhost multi-process distributed benchmarks.
All outputs are saved to isolated timestamped directories under benchmarks/experiment_runs/
to guarantee historical benchmark artifacts are never overwritten.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import platform
import random
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import numpy as np
import psutil

from taskmesh.core.enums import NodeStatus, OffloadPolicy, SchedulerMode
from taskmesh.core.models import (
    BinaryPayloadMeta,
    NodeCapabilities,
    NodeProfile,
    NodeTelemetry,
    Task,
)
from taskmesh.fairness.drr import calculate_fairness_cv
from taskmesh.learning.mwu import MWUWeightLearner
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.baseline import (
    HighestBidScheduler,
    LeastLoadedScheduler,
    RoundRobinScheduler,
)
from taskmesh.wireless.estimator import NetworkEstimator, NodeNetworkMetrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("taskmesh.experiment")


# ==============================================================================
# 1. System Environment Metadata Snapshot
# ==============================================================================

def capture_system_environment() -> Dict[str, Any]:
    """Captures exact hardware, operating system, and Python environment metadata."""
    cuda_available = False
    cuda_device = None
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            cuda_device = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # Git metadata
    git_revision = "unknown"
    git_branch = "unknown"
    git_clean = False
    try:
        git_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        status_output = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        git_clean = (len(status_output) == 0)
    except Exception:
        pass

    mem = psutil.virtual_memory()

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision,
        "git_branch": git_branch,
        "git_working_tree_clean": git_clean,
        "os": platform.platform(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "ram_available_gb": round(mem.available / (1024 ** 3), 2),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "cuda_available": cuda_available,
        "cuda_device": cuda_device,
    }


# ==============================================================================
# 2. Cluster Profiles (Homogeneous, Heterogeneous, Simulated Wireless)
# ==============================================================================

def create_homogeneous_cluster() -> List[NodeProfile]:
    """Creates a 4-node cluster where all nodes have identical hardware capabilities."""
    nodes = []
    for i in range(4):
        nid = f"homo-node-{i+1}"
        nodes.append(
            NodeProfile(
                id=nid,
                status=NodeStatus.ONLINE,
                capabilities=NodeCapabilities(
                    cpu_cores=4,
                    cpu_frequency_mhz=2500.0,
                    ram_total_mb=8192,
                    ram_available_mb=6000,
                    has_gpu=False,
                    supported_handlers=["cpu_test", "log", "image_inference"],
                    tags=["standard", "cpu"],
                ),
                telemetry=NodeTelemetry(
                    node_id=nid,
                    cpu_percent=30.0,
                    ram_percent=40.0,
                    network_latency_ms=2.0,
                    rtt_ms_ewma=2.0,
                    upload_mbps_ewma=100.0,
                    download_mbps_ewma=100.0,
                ),
                base_score=1.0,
            )
        )
    return nodes


def create_heterogeneous_cluster() -> List[NodeProfile]:
    """Creates a 4-node heterogeneous cluster with clearly labeled simulated hardware profiles."""
    n1 = NodeProfile(
        id="node-gpu-rig",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=16,
            cpu_frequency_mhz=3800.0,
            ram_total_mb=32768,
            ram_available_mb=28000,
            has_gpu=True,
            gpu_name="NVIDIA RTX 4090 (Simulated)",
            supported_handlers=["cpu_test", "log", "image_inference"],
            tags=["gpu", "cuda", "fast"],
        ),
        telemetry=NodeTelemetry(node_id="node-gpu-rig", cpu_percent=15.0, ram_percent=25.0, network_latency_ms=1.2),
        base_score=2.8,
    )
    n2 = NodeProfile(
        id="node-cpu-server",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=12,
            cpu_frequency_mhz=3200.0,
            ram_total_mb=16384,
            ram_available_mb=12000,
            has_gpu=False,
            supported_handlers=["cpu_test", "log", "image_inference"],
            tags=["cpu", "fast"],
        ),
        telemetry=NodeTelemetry(node_id="node-cpu-server", cpu_percent=20.0, ram_percent=35.0, network_latency_ms=2.0),
        base_score=1.8,
    )
    n3 = NodeProfile(
        id="node-laptop",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=4,
            cpu_frequency_mhz=2400.0,
            ram_total_mb=8192,
            ram_available_mb=4096,
            has_gpu=False,
            supported_handlers=["cpu_test", "log", "image_inference"],
            tags=["cpu", "general"],
        ),
        telemetry=NodeTelemetry(node_id="node-laptop", cpu_percent=45.0, ram_percent=60.0, network_latency_ms=5.0),
        base_score=1.0,
    )
    n4 = NodeProfile(
        id="node-edge-mini",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=2,
            cpu_frequency_mhz=1800.0,
            ram_total_mb=4096,
            ram_available_mb=2048,
            has_gpu=False,
            supported_handlers=["cpu_test", "log", "image_inference"],
            tags=["cpu", "low-power"],
        ),
        telemetry=NodeTelemetry(node_id="node-edge-mini", cpu_percent=60.0, ram_percent=70.0, network_latency_ms=8.5),
        base_score=0.6,
    )
    return [n1, n2, n3, n4]


def create_wireless_edge_cluster(network_profile: Optional[Dict[str, float]] = None) -> Tuple[List[NodeProfile], NetworkEstimator]:
    """Creates a local laptop + remote GPU rig + remote edge Pi with simulated network profiles."""
    net = network_profile or {"rtt_ms": 25.0, "upload_mbps": 40.0, "download_mbps": 60.0}

    local_laptop = NodeProfile(
        id="local-laptop",
        status=NodeStatus.ONLINE,
        is_local=True,
        capabilities=NodeCapabilities(
            cpu_cores=4,
            cpu_frequency_mhz=2200.0,
            ram_total_mb=8192,
            ram_available_mb=4096,
            has_gpu=False,
            is_local=True,
            supported_handlers=["image_inference", "cpu_test", "log"],
            tags=["client", "local", "cpu"],
        ),
        telemetry=NodeTelemetry(
            node_id="local-laptop",
            cpu_percent=50.0,
            ram_percent=55.0,
            network_latency_ms=0.5,
            rtt_ms_ewma=0.5,
            upload_mbps_ewma=1000.0,
            download_mbps_ewma=1000.0,
        ),
        base_score=1.0,
    )

    wifi_gpu = NodeProfile(
        id="wifi-gpu-rig",
        status=NodeStatus.ONLINE,
        is_local=False,
        capabilities=NodeCapabilities(
            cpu_cores=16,
            cpu_frequency_mhz=3800.0,
            ram_total_mb=32768,
            ram_available_mb=26000,
            has_gpu=True,
            gpu_name="NVIDIA RTX 4080 (Simulated)",
            supported_handlers=["image_inference", "cpu_test", "log"],
            tags=["gpu", "cuda", "wifi-remote"],
        ),
        telemetry=NodeTelemetry(
            node_id="wifi-gpu-rig",
            cpu_percent=12.0,
            ram_percent=20.0,
            network_latency_ms=net["rtt_ms"],
            rtt_ms_ewma=net["rtt_ms"],
            upload_mbps_ewma=net["upload_mbps"],
            download_mbps_ewma=net["download_mbps"],
        ),
        base_score=3.5,
    )

    wifi_pi = NodeProfile(
        id="wifi-edge-pi",
        status=NodeStatus.ONLINE,
        is_local=False,
        capabilities=NodeCapabilities(
            cpu_cores=4,
            cpu_frequency_mhz=1500.0,
            ram_total_mb=4096,
            ram_available_mb=2048,
            has_gpu=False,
            supported_handlers=["image_inference", "cpu_test", "log"],
            tags=["edge", "wifi-remote"],
        ),
        telemetry=NodeTelemetry(
            node_id="wifi-edge-pi",
            cpu_percent=65.0,
            ram_percent=70.0,
            network_latency_ms=net["rtt_ms"] * 1.4,
            rtt_ms_ewma=net["rtt_ms"] * 1.4,
            upload_mbps_ewma=max(1.0, net["upload_mbps"] * 0.5),
            download_mbps_ewma=max(2.0, net["download_mbps"] * 0.5),
        ),
        base_score=0.8,
    )

    estimator = NetworkEstimator()
    # Pre-populate estimator telemetry
    m_local = estimator.get_or_create_metrics("local-laptop", is_local=True)
    m_local.rtt_ms_ewma = 0.5
    m_local.upload_mbps_ewma = 1000.0
    m_local.download_mbps_ewma = 1000.0

    m_gpu = estimator.get_or_create_metrics("wifi-gpu-rig", is_local=False)
    m_gpu.rtt_ms_ewma = net["rtt_ms"]
    m_gpu.upload_mbps_ewma = net["upload_mbps"]
    m_gpu.download_mbps_ewma = net["download_mbps"]

    m_pi = estimator.get_or_create_metrics("wifi-edge-pi", is_local=False)
    m_pi.rtt_ms_ewma = net["rtt_ms"] * 1.4
    m_pi.upload_mbps_ewma = max(1.0, net["upload_mbps"] * 0.5)
    m_pi.download_mbps_ewma = max(2.0, net["download_mbps"] * 0.5)

    return [local_laptop, wifi_gpu, wifi_pi], estimator


# ==============================================================================
# 3. Workload Generators for Scenarios A to H
# ==============================================================================

def generate_workload(scenario: str, num_tasks: int = 100, seed: int = 42) -> List[Task]:
    """Generates deterministic, repeatable task workloads for experimental scenarios."""
    rng = random.Random(seed)
    tasks = []

    for i in range(num_tasks):
        tid = f"task_{scenario}_{seed}_{i:04d}"

        if scenario == "A_homogeneous":
            prio = rng.randint(1, 20)
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test",
                    priority=prio,
                    requires_gpu=False,
                    payload={"iterations": 500 + (i % 10) * 100},
                )
            )

        elif scenario == "B_heterogeneous":
            prio = rng.randint(1, 20)
            req_gpu = (i % 5 == 0)
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test" if not req_gpu else "image_inference",
                    priority=prio,
                    requires_gpu=req_gpu,
                    payload={"iterations": 500 + (i % 10) * 100},
                )
            )

        elif scenario == "C_uneven_arrivals":
            # Bursty arrival pattern: bursts of 10 tasks followed by spacing
            prio = rng.randint(1, 15)
            burst_group = i // 10
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test",
                    priority=prio,
                    payload={"burst_group": burst_group, "iterations": 400},
                )
            )

        elif scenario == "D_uneven_execution_time":
            # Bimodal execution: 80% light tasks (iterations=100), 20% heavy tasks (iterations=2500)
            is_heavy = (rng.random() < 0.20)
            iters = 2500 if is_heavy else 100
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test",
                    priority=15 if is_heavy else 5,
                    payload={"iterations": iters, "is_heavy": is_heavy},
                )
            )

        elif scenario == "E_changing_load":
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test",
                    priority=rng.randint(1, 10),
                    payload={"iterations": 600},
                )
            )

        elif scenario == "F_node_failure":
            tasks.append(
                Task(
                    id=tid,
                    task_type="cpu_test",
                    priority=rng.randint(1, 20),
                    payload={"iterations": 500},
                )
            )

        elif scenario == "G_inference_payloads":
            # Image inference tasks with varying payload sizes (50KB to 5MB)
            sizes_kb = [50, 200, 500, 1500, 3000, 5000]
            size_kb = sizes_kb[i % len(sizes_kb)]
            payload_bytes = size_kb * 1024
            meta = BinaryPayloadMeta(
                task_id=tid,
                size_bytes=payload_bytes,
                mime_type="image/jpeg",
                checksum_sha256=f"hash_{tid}",
            )
            tasks.append(
                Task(
                    id=tid,
                    task_type="image_inference",
                    offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
                    binary_meta=meta,
                    priority=rng.randint(1, 15),
                    payload={"model": "yolov8n", "payload_size": payload_bytes},
                )
            )

        elif scenario == "H_wireless_cost":
            sizes_kb = [100, 500, 2000, 5000]
            size_kb = sizes_kb[i % len(sizes_kb)]
            payload_bytes = size_kb * 1024
            meta = BinaryPayloadMeta(
                task_id=tid,
                size_bytes=payload_bytes,
                mime_type="image/jpeg",
                checksum_sha256=f"hash_{tid}",
            )
            tasks.append(
                Task(
                    id=tid,
                    task_type="image_inference",
                    offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
                    binary_meta=meta,
                    priority=10,
                    payload={"payload_size": payload_bytes},
                )
            )

        else:
            tasks.append(Task(id=tid, task_type="cpu_test", priority=5))

    return tasks


# ==============================================================================
# 4. Metrics & Statistics Helper
# ==============================================================================

def compute_statistics(values: List[float]) -> Dict[str, float]:
    """Computes mean, median (p50), p95, and max of a series."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0}
    arr = np.array(values, dtype=np.float64)
    return {
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "p95": round(float(np.percentile(arr, 95)), 4),
        "max": round(float(np.max(arr)), 4),
    }


# ==============================================================================
# 5. Microbenchmark Runner for Schedulers & Ablations
# ==============================================================================

def create_scheduler(policy_name: str) -> Any:
    """Instantiates a fresh scheduler according to policy or ablation name."""
    if policy_name == "round_robin":
        return RoundRobinScheduler()
    elif policy_name == "least_loaded":
        return LeastLoadedScheduler()
    elif policy_name == "highest_bid":
        return HighestBidScheduler()
    elif policy_name == "adaptive_full":
        return AdaptiveScheduler()
    elif policy_name == "ablation_no_ewma":
        return AdaptiveScheduler(enable_ewma=False)
    elif policy_name == "ablation_no_drr":
        return AdaptiveScheduler(enable_drr=False)
    elif policy_name == "ablation_no_bidding":
        return AdaptiveScheduler(enable_bidding=False)
    elif policy_name == "ablation_no_mwu":
        return AdaptiveScheduler(enable_mwu=False)
    elif policy_name == "ablation_no_rl":
        return AdaptiveScheduler(enable_rl=False)
    elif policy_name == "ablation_no_wireless":
        return AdaptiveScheduler(enable_wireless_cost=False)
    else:
        raise ValueError(f"Unknown policy name: {policy_name}")


async def run_single_microbenchmark_trial(
    policy_name: str,
    workload: List[Task],
    cluster_factory: Callable[[], List[NodeProfile]],
    scenario: str,
    trial_idx: int,
) -> Dict[str, Any]:
    """Runs a single microbenchmark trial with fresh scheduler and isolated nodes."""
    nodes = cluster_factory()
    node_map = {n.id: n for n in nodes}
    scheduler = create_scheduler(policy_name)

    scheduling_latencies_ms: List[float] = []
    task_allocations: Dict[str, int] = {n.id: 0 for n in nodes}
    offload_decisions: Dict[str, int] = {"local": 0, "remote": 0}
    decisions_list = []

    t_start = time.perf_counter()

    for idx, task in enumerate(workload):
        # Scenario E: Dynamic node load fluctuation
        if scenario == "E_changing_load" and idx % 20 == 0:
            for n in nodes:
                if n.telemetry:
                    n.telemetry.cpu_percent = float(10 + ((idx * 17) % 75))
                    n.telemetry.ram_percent = float(20 + ((idx * 13) % 65))

        # Scenario F: Node failure halfway through
        if scenario == "F_node_failure" and idx == len(workload) // 2:
            # Drop the top capability node
            nodes[0].status = NodeStatus.OFFLINE

        t0 = time.perf_counter()
        decision = await scheduler.select_node(task, nodes)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        scheduling_latencies_ms.append(dt_ms)

        selected_id = decision.selected_node_id
        task_allocations[selected_id] = task_allocations.get(selected_id, 0) + 1
        node = node_map[selected_id]
        node.total_completed += 1

        if decision.offload_decision == "remote":
            offload_decisions["remote"] += 1
        else:
            offload_decisions["local"] += 1

        # Simulate outcome feedback loop for adaptive schedulers
        if isinstance(scheduler, AdaptiveScheduler):
            # Compute simulated execution time based on task iterations and node capability
            iters = task.payload.get("iterations", 500) if isinstance(task.payload, dict) else 500
            simulated_exec = (iters / 10000.0) / max(0.2, node.base_score)
            await scheduler.record_task_outcome(
                node=node,
                task=task,
                decision=decision,
                actual_duration_seconds=simulated_exec,
                success=True,
            )

        decisions_list.append(decision)

    total_duration = time.perf_counter() - t_start
    throughput = len(workload) / max(0.0001, total_duration)

    counts = [task_allocations.get(n.id, 0) for n in nodes]
    fairness_cv = calculate_fairness_cv(counts)
    latency_stats = compute_statistics(scheduling_latencies_ms)

    return {
        "policy": policy_name,
        "scenario": scenario,
        "trial_idx": trial_idx + 1,
        "total_tasks": len(workload),
        "total_time_seconds": round(total_duration, 5),
        "throughput_tasks_per_sec": round(throughput, 1),
        "decision_latency_mean_ms": latency_stats["mean"],
        "decision_latency_p50_ms": latency_stats["median"],
        "decision_latency_p95_ms": latency_stats["p95"],
        "decision_latency_max_ms": latency_stats["max"],
        "fairness_cv": fairness_cv,
        "task_allocations": task_allocations,
        "offload_decisions": offload_decisions,
    }


async def evaluate_microbenchmark_policy(
    policy_name: str,
    scenario: str,
    cluster_factory: Callable[[], List[NodeProfile]],
    num_tasks: int = 150,
    repetitions: int = 5,
    base_seed: int = 42,
) -> Dict[str, Any]:
    """Runs multiple repetitions of a policy across identical pre-generated workloads."""
    trial_results = []
    for rep in range(repetitions):
        seed = base_seed + rep * 101
        workload = generate_workload(scenario=scenario, num_tasks=num_tasks, seed=seed)
        res = await run_single_microbenchmark_trial(
            policy_name=policy_name,
            workload=workload,
            cluster_factory=cluster_factory,
            scenario=scenario,
            trial_idx=rep,
        )
        trial_results.append(res)

    # Aggregate across repetitions
    throughputs = [t["throughput_tasks_per_sec"] for t in trial_results]
    p50_lats = [t["decision_latency_p50_ms"] for t in trial_results]
    p95_lats = [t["decision_latency_p95_ms"] for t in trial_results]
    mean_lats = [t["decision_latency_mean_ms"] for t in trial_results]
    fairness_cvs = [t["fairness_cv"] for t in trial_results]

    all_node_keys = list(trial_results[0]["task_allocations"].keys())
    mean_allocations = {
        nid: round(float(np.mean([t["task_allocations"].get(nid, 0) for t in trial_results])), 1)
        for nid in all_node_keys
    }

    return {
        "policy": policy_name,
        "scenario": scenario,
        "repetitions": repetitions,
        "tasks_per_trial": num_tasks,
        "throughput_tasks_per_sec": compute_statistics(throughputs),
        "decision_latency_mean_ms": compute_statistics(mean_lats),
        "decision_latency_p50_ms": compute_statistics(p50_lats),
        "decision_latency_p95_ms": compute_statistics(p95_lats),
        "fairness_cv": compute_statistics(fairness_cvs),
        "mean_allocations": mean_allocations,
        "trials": trial_results,
    }


# ==============================================================================
# 6. Controlled Network Simulation (Phase 4)
# ==============================================================================

NETWORK_PROFILES = {
    "fast_network": {"rtt_ms": 2.0, "upload_mbps": 300.0, "download_mbps": 300.0, "description": "Low latency, high bandwidth (Wi-Fi 6 near router)"},
    "typical_network": {"rtt_ms": 25.0, "upload_mbps": 40.0, "download_mbps": 60.0, "description": "Moderate latency and bandwidth (typical 2.4/5GHz Wi-Fi)"},
    "constrained_network": {"rtt_ms": 120.0, "upload_mbps": 5.0, "download_mbps": 10.0, "description": "High latency, constrained bandwidth (weak signal / edge)"},
    "congested_network": {"rtt_ms": 85.0, "upload_mbps": 12.0, "download_mbps": 18.0, "description": "Variable network condition with queue congestion"},
}


async def run_network_model_evaluation(payload_sizes_kb: List[int]) -> Dict[str, Any]:
    """Experiment 1: Scheduling Model Evaluation.
    Evaluates whether the NetworkEstimator makes sensible local vs remote offload decisions
    given injected telemetry without introducing wall-clock sleep delays.
    """
    model_results = {}
    for prof_name, prof_cfg in NETWORK_PROFILES.items():
        nodes, estimator = create_wireless_edge_cluster(network_profile=prof_cfg)
        local_node = nodes[0]
        remote_gpu = nodes[1]

        prof_decisions = []
        for size_kb in payload_sizes_kb:
            payload_bytes = size_kb * 1024
            meta = BinaryPayloadMeta(
                task_id=f"sim_net_{size_kb}k",
                size_bytes=payload_bytes,
                mime_type="image/jpeg",
                checksum_sha256="test",
            )
            task = Task(
                id=f"task_{size_kb}k",
                task_type="image_inference",
                offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
                binary_meta=meta,
            )

            comp = estimator.compare_local_vs_remote(
                task=task,
                local_node=local_node,
                remote_node=remote_gpu,
                payload_size_bytes=payload_bytes,
            )
            rem = comp["remote_details"]

            prof_decisions.append({
                "payload_size_kb": size_kb,
                "local_estimate_ms": comp["local_estimate_ms"],
                "remote_estimate_ms": comp["remote_estimate_ms"],
                "upload_ms": rem["upload_ms"],
                "download_ms": rem["download_ms"],
                "remote_infer_ms": rem["remote_inference_ms"],
                "decision": comp["decision"],
                "reason": comp["reason"],
            })

        model_results[prof_name] = {
            "profile_config": prof_cfg,
            "decisions": prof_decisions,
        }

    return model_results


async def run_simulated_transport_evaluation(
    payload_sizes_kb: List[int],
    repetitions: int = 5,
    seed: int = 42,
) -> Dict[str, Any]:
    """Experiment 2: Simulated Transport Evaluation.
    Applies controlled mathematical delay model based on payload size and network bandwidth:
    Delta_t_transfer = (size_bytes * 8) / (mbps * 1e6) + (RTT / 1000)
    Measures and compares simulated wall-clock end-to-end task duration for local vs remote.
    """
    rng = random.Random(seed)
    transport_results = {}

    for prof_name, prof_cfg in NETWORK_PROFILES.items():
        rtt_sec = prof_cfg["rtt_ms"] / 1000.0
        up_speed_bps = prof_cfg["upload_mbps"] * 1e6
        down_speed_bps = prof_cfg["download_mbps"] * 1e6

        size_metrics = []
        for size_kb in payload_sizes_kb:
            payload_bytes = size_kb * 1024
            transfer_times_sec = []

            for _ in range(repetitions):
                # Add 5% simulated jitter
                jitter = rng.uniform(0.95, 1.05)
                up_time = (payload_bytes * 8.0) / up_speed_bps * jitter
                down_time = (1024 * 8.0) / down_speed_bps * jitter
                total_network_delay = up_time + rtt_sec * jitter + down_time
                transfer_times_sec.append(total_network_delay * 1000.0)

            # Local CPU inference compute time ~ 135 ms (simulated)
            local_infer_ms = 135.0
            # Remote GPU inference compute time ~ 28 ms (simulated)
            remote_gpu_infer_ms = 28.0

            avg_trans_ms = float(np.mean(transfer_times_sec))
            simulated_remote_e2e_ms = round(avg_trans_ms + remote_gpu_infer_ms, 2)
            simulated_local_e2e_ms = round(local_infer_ms, 2)

            optimal_choice = "remote" if simulated_remote_e2e_ms < simulated_local_e2e_ms else "local"

            size_metrics.append({
                "payload_size_kb": size_kb,
                "simulated_transfer_delay_ms": compute_statistics(transfer_times_sec),
                "simulated_local_e2e_ms": simulated_local_e2e_ms,
                "simulated_remote_e2e_ms": simulated_remote_e2e_ms,
                "optimal_choice": optimal_choice,
                "advantage_ms": round(abs(simulated_local_e2e_ms - simulated_remote_e2e_ms), 2),
            })

        transport_results[prof_name] = {
            "profile_config": prof_cfg,
            "metrics": size_metrics,
        }

    return transport_results


# ==============================================================================
# 7. Localhost Multi-Process Distributed Benchmark
# ==============================================================================

DISTRIBUTED_SIMULATED_NODES = [
    {"node_id": "sim-gpu-rig", "workers": 4, "tags": "gpu,cuda,fast", "cores": 16, "ram_mb": 32768, "has_gpu": True},
    {"node_id": "sim-cpu-server", "workers": 4, "tags": "cpu,server", "cores": 12, "ram_mb": 16384, "has_gpu": False},
    {"node_id": "sim-laptop", "workers": 2, "tags": "laptop,general", "cores": 4, "ram_mb": 8192, "has_gpu": False},
    {"node_id": "sim-edge-mini", "workers": 1, "tags": "edge,low-power", "cores": 2, "ram_mb": 4096, "has_gpu": False},
]


async def run_single_distributed_trial(
    policy: str,
    trial_idx: int,
    num_tasks: int = 40,
    base_port: int = 9100,
) -> Dict[str, Any]:
    """Runs a genuine multi-process distributed benchmark over WebSockets on localhost."""
    python_bin = sys.executable
    port = base_port + (trial_idx * 15)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    processes = []

    try:
        # 1. Start Orchestrator OS process
        orch_mode = "adaptive" if policy in ("adaptive", "adaptive_full") else policy
        orch_cmd = [
            python_bin, "-m", "taskmesh.orchestrator.main",
            "--port", str(port),
            "--mode", orch_mode,
            "--db", db_path,
        ]
        p_orch = subprocess.Popen(orch_cmd)
        processes.append(("Orchestrator", p_orch))

        # Wait for orchestrator health
        async with httpx.AsyncClient(timeout=2.0) as client:
            ready = False
            for _ in range(35):
                try:
                    resp = await client.get(f"http://127.0.0.1:{port}/v1/cluster/health")
                    if resp.status_code == 200:
                        ready = True
                        break
                except Exception:
                    await asyncio.sleep(0.2)
            if not ready:
                raise RuntimeError(f"Orchestrator failed to initialize on port {port}")

        # 2. Spawn independent Node processes
        ws_url = f"ws://127.0.0.1:{port}/v1/ws/nodes"
        for n_cfg in DISTRIBUTED_SIMULATED_NODES:
            node_cmd = [
                python_bin, "-m", "taskmesh.node.main",
                "--node-id", n_cfg["node_id"],
                "--url", ws_url,
                "--workers", str(n_cfg["workers"]),
                "--tags", n_cfg["tags"],
                "--heartbeat-interval", "0.5",
            ]
            p_node = subprocess.Popen(node_cmd)
            processes.append((n_cfg["node_id"], p_node))

        # Wait for all nodes to connect
        async with httpx.AsyncClient(timeout=2.0) as client:
            nodes_ready = False
            for _ in range(40):
                try:
                    h_resp = await client.get(f"http://127.0.0.1:{port}/v1/cluster/health")
                    if h_resp.status_code == 200 and h_resp.json().get("online_nodes", 0) >= len(DISTRIBUTED_SIMULATED_NODES):
                        nodes_ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.2)
            if not nodes_ready:
                raise RuntimeError(f"Nodes failed to connect to orchestrator on port {port}")

        # 3. Submit mixed workload
        task_ids = []
        submission_times = {}
        t_start = time.perf_counter()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(num_tasks):
                if i % 3 == 0:
                    req = {"task_type": "cpu_test", "payload": {"iterations": 800}, "priority": 10}
                elif i % 3 == 1:
                    req = {"task_type": "image_inference", "payload": {"batch_size": 1, "image_dim": 64}, "priority": 5}
                else:
                    req = {"task_type": "log", "payload": {"message": f"e2e-task-{i}"}, "priority": 1}

                t_sub = time.perf_counter()
                r = await client.post(f"http://127.0.0.1:{port}/v1/tasks", json=req)
                tid = r.json()["id"]
                task_ids.append(tid)
                submission_times[tid] = t_sub

            # 4. Wait for task completion
            completed_tasks = {}
            for _ in range(70):
                for tid in task_ids:
                    if tid not in completed_tasks:
                        res = await client.get(f"http://127.0.0.1:{port}/v1/tasks/{tid}")
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("status") == "completed":
                                completed_tasks[tid] = (time.perf_counter(), data)
                if len(completed_tasks) == num_tasks:
                    break
                await asyncio.sleep(0.2)

            t_end = time.perf_counter()
            total_time = t_end - t_start

            # Fetch scheduler decisions
            dec_resp = await client.get(f"http://127.0.0.1:{port}/v1/scheduler/decisions?limit=200")
            decisions = dec_resp.json() if dec_resp.status_code == 200 else []

        # 5. Calculate Metrics
        e2e_latencies = []
        task_dist = {n["node_id"]: 0 for n in DISTRIBUTED_SIMULATED_NODES}

        for tid, (comp_time, t_data) in completed_tasks.items():
            e2e_lat = comp_time - submission_times[tid]
            e2e_latencies.append(e2e_lat)
            assigned = t_data.get("assigned_node_id")
            if assigned in task_dist:
                task_dist[assigned] += 1

        scheduling_latencies = [d["decision_latency_ms"] for d in decisions if "decision_latency_ms" in d]
        avg_sched_lat = float(np.mean(scheduling_latencies)) if scheduling_latencies else 0.05
        throughput = float(len(completed_tasks) / total_time) if total_time > 0 else 0.0
        fairness_cv = calculate_fairness_cv(list(task_dist.values()))

        return {
            "policy": policy,
            "trial": trial_idx + 1,
            "total_tasks": num_tasks,
            "completed_tasks": len(completed_tasks),
            "total_time_seconds": round(total_time, 3),
            "throughput_tasks_per_sec": round(throughput, 2),
            "e2e_latency_stats_seconds": compute_statistics(e2e_latencies),
            "avg_scheduling_latency_ms": round(avg_sched_lat, 3),
            "fairness_cv": round(fairness_cv, 4),
            "task_distribution": task_dist,
            "failures": 0,
        }

    finally:
        for name, p in reversed(processes):
            try:
                p.terminate()
            except Exception:
                pass
            try:
                p.kill()
            except Exception:
                pass

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


async def run_distributed_policy_evaluation(
    policy: str,
    num_trials: int = 5,
    num_tasks: int = 40,
    base_port: int = 9100,
) -> Dict[str, Any]:
    """Runs distributed benchmark repetitions for a given policy."""
    trials = []
    for t_idx in range(num_trials):
        port = base_port + (t_idx * 15)
        res = await run_single_distributed_trial(policy=policy, trial_idx=t_idx, num_tasks=num_tasks, base_port=port)
        trials.append(res)

    throughputs = [t["throughput_tasks_per_sec"] for t in trials]
    p50_e2e = [t["e2e_latency_stats_seconds"]["median"] for t in trials]
    p95_e2e = [t["e2e_latency_stats_seconds"]["p95"] for t in trials]
    mean_e2e = [t["e2e_latency_stats_seconds"]["mean"] for t in trials]
    fairness_cvs = [t["fairness_cv"] for t in trials]

    all_nids = list(trials[0]["task_distribution"].keys())
    mean_distribution = {
        nid: round(float(np.mean([t["task_distribution"][nid] for t in trials])), 1)
        for nid in all_nids
    }

    return {
        "policy": policy,
        "num_trials": num_trials,
        "tasks_per_trial": num_tasks,
        "throughput_tasks_per_sec": compute_statistics(throughputs),
        "e2e_latency_mean_sec": compute_statistics(mean_e2e),
        "e2e_latency_p50_sec": compute_statistics(p50_e2e),
        "e2e_latency_p95_sec": compute_statistics(p95_e2e),
        "fairness_cv": compute_statistics(fairness_cvs),
        "mean_task_distribution": mean_distribution,
        "trial_details": trials,
    }


# ==============================================================================
# 8. Master Experiment Orchestrator & CLI Runner
# ==============================================================================

async def run_full_experiment_campaign(
    output_dir: str,
    repetitions: int = 5,
    microbench_tasks: int = 150,
    distributed_tasks: int = 40,
    distributed_trials: int = 3,
) -> Dict[str, Any]:
    """Executes the complete comprehensive evaluation campaign."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Starting TaskMesh Evaluation Campaign. Output directory: {output_dir}")

    # Step 1: Environment Snapshot
    env_info = capture_system_environment()
    with open(os.path.join(output_dir, "environment.json"), "w") as f:
        json.dump(env_info, f, indent=2)
    logger.info(f"Captured environment snapshot: OS={env_info['os']}, CPU cores={env_info['logical_cores']}")

    # Step 2: Policy Microbenchmarks across Scenarios
    policies = [
        "round_robin",
        "least_loaded",
        "highest_bid",
        "adaptive_full",
        "ablation_no_ewma",
        "ablation_no_drr",
        "ablation_no_bidding",
        "ablation_no_mwu",
        "ablation_no_rl",
        "ablation_no_wireless",
    ]

    scenarios = [
        ("A_homogeneous", create_homogeneous_cluster),
        ("B_heterogeneous", create_heterogeneous_cluster),
        ("C_uneven_arrivals", create_heterogeneous_cluster),
        ("D_uneven_execution_time", create_heterogeneous_cluster),
        ("E_changing_load", create_heterogeneous_cluster),
        ("F_node_failure", create_heterogeneous_cluster),
        ("G_inference_payloads", create_heterogeneous_cluster),
    ]

    microbench_results: Dict[str, Dict[str, Any]] = {}
    for sc_name, cluster_fn in scenarios:
        logger.info(f"Running Scenario: {sc_name} across {len(policies)} policies ({repetitions} repetitions each)...")
        microbench_results[sc_name] = {}
        for pol in policies:
            res = await evaluate_microbenchmark_policy(
                policy_name=pol,
                scenario=sc_name,
                cluster_factory=cluster_fn,
                num_tasks=microbench_tasks,
                repetitions=repetitions,
                base_seed=42,
            )
            microbench_results[sc_name][pol] = res
            logger.info(f"  [{sc_name}] [{pol}] Throughput={res['throughput_tasks_per_sec']['mean']} t/s | "
                        f"p50_lat={res['decision_latency_p50_ms']['mean']} ms | CV={res['fairness_cv']['mean']}")

    with open(os.path.join(output_dir, "microbenchmark_results.json"), "w") as f:
        json.dump(microbench_results, f, indent=2)

    # Step 3: Network Condition Simulations (Phase 4)
    logger.info("Running Controlled Network Simulation (Experiment 1: Cost Model, Experiment 2: Transport Delay)...")
    payload_sizes = [50, 200, 500, 1000, 2048, 5120]
    exp1_model = await run_network_model_evaluation(payload_sizes)
    exp2_transport = await run_simulated_transport_evaluation(payload_sizes, repetitions=repetitions)

    network_results = {
        "experiment_1_model_decisions": exp1_model,
        "experiment_2_transport_delay": exp2_transport,
    }
    with open(os.path.join(output_dir, "network_simulation_results.json"), "w") as f:
        json.dump(network_results, f, indent=2)

    # Step 4: Multi-Process Distributed Execution (Localhost)
    dist_policies = ["round_robin", "least_loaded", "highest_bid", "adaptive"]
    logger.info(f"Running Multi-Process Distributed Suite across {dist_policies} ({distributed_trials} trials of {distributed_tasks} tasks)...")
    distributed_results: Dict[str, Any] = {}
    port_offset = 9200
    for pol in dist_policies:
        logger.info(f"  Spawning distributed processes for policy: {pol}...")
        dist_res = await run_distributed_policy_evaluation(
            policy=pol,
            num_trials=distributed_trials,
            num_tasks=distributed_tasks,
            base_port=port_offset,
        )
        distributed_results[pol] = dist_res
        port_offset += 60
        logger.info(f"  [{pol}] Distributed Throughput={dist_res['throughput_tasks_per_sec']['mean']} t/s | "
                    f"p50_e2e={dist_res['e2e_latency_p50_sec']['mean']}s | CV={dist_res['fairness_cv']['mean']}")

    with open(os.path.join(output_dir, "distributed_results.json"), "w") as f:
        json.dump(distributed_results, f, indent=2)

    # Summary manifest
    summary = {
        "campaign_completed_at": datetime.now(timezone.utc).isoformat(),
        "environment": env_info,
        "scenarios_evaluated": list(microbench_results.keys()),
        "policies_evaluated": policies,
        "network_profiles": list(NETWORK_PROFILES.keys()),
        "output_directory": output_dir,
    }
    with open(os.path.join(output_dir, "campaign_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"All experiments completed successfully. Results saved in {output_dir}")
    return summary


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("benchmarks", "experiment_runs", f"run_{timestamp}")

    repetitions = 5
    microbench_tasks = 150
    distributed_tasks = 40
    distributed_trials = 3

    if "--quick" in sys.argv:
        repetitions = 3
        microbench_tasks = 80
        distributed_tasks = 25
        distributed_trials = 2

    asyncio.run(
        run_full_experiment_campaign(
            output_dir=out_dir,
            repetitions=repetitions,
            microbench_tasks=microbench_tasks,
            distributed_tasks=distributed_tasks,
            distributed_trials=distributed_trials,
        )
    )


if __name__ == "__main__":
    main()
