"""RECONCILIATION BENCHMARK FOR Q-LEARNING AND MWU ABLATIONS

Compares under identical workloads and fresh scheduler instances:
1. Full Adaptive with Epsilon Decay (epsilon 0.15 -> 0.01)
2. Full Adaptive with Fixed Epsilon (epsilon 0.15 fixed)
3. Ablation without Q-learning (enable_rl=False)
4. Full Adaptive with MWU (adaptive factor weights)
5. Ablation without MWU (enable_mwu=False, fixed uniform weights)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taskmesh.core.models import NodeProfile, Task
from taskmesh.fairness.drr import calculate_fairness_cv
from taskmesh.learning.qlearning import QLearningScheduler
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from benchmarks.experiment_runner import (
    create_heterogeneous_cluster,
    generate_workload,
    compute_statistics,
)


async def run_trial(
    sched: AdaptiveScheduler,
    tasks: List[Task],
) -> Dict[str, Any]:
    nodes = create_heterogeneous_cluster()
    node_map = {n.id: n for n in nodes}
    allocations = {n.id: 0 for n in nodes}
    latencies_ms = []

    t0 = time.perf_counter()
    for task in tasks:
        t_dec = time.perf_counter()
        dec = await sched.select_node(task, nodes)
        dt = (time.perf_counter() - t_dec) * 1000.0
        latencies_ms.append(dt)

        nid = dec.selected_node_id
        allocations[nid] += 1
        node = node_map[nid]
        node.total_completed += 1

        simulated_time = 0.05 / max(0.5, node.base_score)
        await sched.record_task_outcome(
            node=node,
            task=task,
            decision=dec,
            actual_duration_seconds=simulated_time,
            success=True,
        )

    total_time = time.perf_counter() - t0
    decisions_per_sec = len(tasks) / max(0.0001, total_time)
    cv = calculate_fairness_cv(list(allocations.values()))

    return {
        "decisions_per_sec": decisions_per_sec,
        "total_time_seconds": total_time,
        "decision_latency_stats_ms": compute_statistics(latencies_ms),
        "fairness_cv": cv,
        "allocations": allocations,
        "final_epsilon": sched.rl.epsilon if sched.enable_rl else 0.0,
        "q_table_size": len(sched.rl.q_table) if sched.enable_rl else 0,
        "mwu_weights": sched.mwu.get_weights() if sched.enable_mwu else {},
    }


async def main() -> None:
    print("=" * 80)
    print("RECONCILIATION: Q-LEARNING & MWU ABLATION REPEATABILITY")
    print("Workload: 200 tasks per trial, 5 repetitions across identical seeds")
    print("=" * 80)

    num_trials = 5
    num_tasks = 200

    configs = {
        "Adaptive (Epsilon Decay)": lambda: AdaptiveScheduler(rl_epsilon=0.15, enable_rl=True, enable_mwu=True),
        "Adaptive (Fixed Epsilon 0.15)": lambda: AdaptiveScheduler(rl_epsilon=0.15, enable_rl=True, enable_mwu=True),
        "Ablation (No Q-Learning)": lambda: AdaptiveScheduler(enable_rl=False, enable_mwu=True),
        "Ablation (No MWU / Uniform)": lambda: AdaptiveScheduler(enable_rl=True, enable_mwu=False),
        "Ablation (No RL & No MWU)": lambda: AdaptiveScheduler(enable_rl=False, enable_mwu=False),
    }

    all_results = {}

    for name, factory in configs.items():
        print(f"\nEvaluating: {name} across {num_trials} repetitions...")
        trials = []
        for rep in range(num_trials):
            # For fixed epsilon, override epsilon_min to 0.15 so it never decays
            sched = factory()
            if name == "Adaptive (Fixed Epsilon 0.15)":
                sched.rl.epsilon_min = 0.15

            workload = generate_workload("B_heterogeneous", num_tasks=num_tasks, seed=42 + rep * 101)
            res = await run_trial(sched, workload)
            trials.append(res)

        throughputs = [t["decisions_per_sec"] for t in trials]
        p50s = [t["decision_latency_stats_ms"]["median"] for t in trials]
        p95s = [t["decision_latency_stats_ms"]["p95"] for t in trials]
        cvs = [t["fairness_cv"] for t in trials]
        epsilons = [t["final_epsilon"] for t in trials]

        all_results[name] = {
            "decisions_per_sec": compute_statistics(throughputs),
            "p50_decision_latency_ms": compute_statistics(p50s),
            "p95_decision_latency_ms": compute_statistics(p95s),
            "fairness_cv": compute_statistics(cvs),
            "final_epsilon": compute_statistics(epsilons),
            "mean_allocations": {
                nid: round(float(np.mean([t["allocations"][nid] for t in trials])), 1)
                for nid in trials[0]["allocations"].keys()
            },
        }

        print(f"  Decision Throughput: {all_results[name]['decisions_per_sec']['mean']:.1f} decisions/sec")
        print(f"  p50 Latency: {all_results[name]['p50_decision_latency_ms']['mean']:.3f} ms | p95 Latency: {all_results[name]['p95_decision_latency_ms']['mean']:.3f} ms")
        print(f"  Fairness CV: {all_results[name]['fairness_cv']['mean']:.3f}")
        print(f"  Allocations: {all_results[name]['mean_allocations']}")
        print(f"  Final Epsilon: {all_results[name]['final_epsilon']['mean']:.4f}")

    out_file = os.path.join("benchmarks", "experiment_runs", "reconciliation_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nReconciliation results saved to: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
