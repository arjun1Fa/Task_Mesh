"""Contract-Net style task bidding protocol and score calculation."""

from typing import Dict, List, Optional
from taskmesh.core.models import NodeProfile, Task


def calculate_node_bid(
    node: NodeProfile,
    task: Task,
    weights: Dict[str, float],
) -> float:
    """Calculates a normalized bid value in [0.0, 1.0] for a node given task and weights."""
    caps = node.capabilities
    telemetry = node.telemetry

    # 1. CPU factor [0, 1]
    cpu_factor = min(1.0, caps.cpu_cores / 16.0)

    # 2. GPU factor [0, 1]
    if task.requires_gpu:
        gpu_factor = 1.0 if caps.has_gpu else 0.0
    else:
        gpu_factor = 0.5

    # 3. Load factor (higher is better -> lower CPU/RAM load) [0, 1]
    if telemetry:
        avg_load = (telemetry.cpu_percent + telemetry.ram_percent) / 200.0
        load_factor = max(0.0, 1.0 - avg_load)
    else:
        load_factor = 0.8

    # 4. Latency & Network factor [0, 1]
    if caps.is_local:
        latency_factor = 1.0
    elif telemetry and (telemetry.rtt_ms_ewma > 0 or telemetry.network_latency_ms > 0):
        effective_rtt = telemetry.rtt_ms_ewma if telemetry.rtt_ms_ewma > 0 else telemetry.network_latency_ms
        rtt_factor = max(0.0, 1.0 - (effective_rtt / 200.0))
        bw_factor = min(1.0, telemetry.upload_mbps_ewma / 100.0) if telemetry.upload_mbps_ewma > 0 else 0.7
        latency_factor = max(0.0, min(1.0, 0.7 * rtt_factor + 0.3 * bw_factor))
    else:
        latency_factor = 0.9

    # 5. Reliability factor [0, 1]
    total_tasks = node.total_completed + node.total_failed
    if total_tasks > 0:
        reliability_factor = node.total_completed / total_tasks
    else:
        reliability_factor = 0.95


    w_cpu = weights.get("cpu", 0.2)
    w_gpu = weights.get("gpu", 0.2)
    w_load = weights.get("load", 0.2)
    w_lat = weights.get("latency", 0.2)
    w_rel = weights.get("reliability", 0.2)

    bid = (
        (w_cpu * cpu_factor)
        + (w_gpu * gpu_factor)
        + (w_load * load_factor)
        + (w_lat * latency_factor)
        + (w_rel * reliability_factor)
    )

    # Multiply by effective score
    final_bid = bid * node.effective_score
    return round(final_bid, 4)
