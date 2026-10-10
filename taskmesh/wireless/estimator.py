"""Network telemetry tracking, EWMA smoothing, and wireless cost estimation."""

import asyncio
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from taskmesh.core.models import NodeProfile, Task


class NodeNetworkMetrics(BaseModel):
    """Network telemetry state per node with EWMA smoothing."""
    node_id: str
    rtt_ms_ewma: float = 20.0
    upload_mbps_ewma: float = 40.0
    download_mbps_ewma: float = 60.0
    transfers_count: int = 0
    total_bytes_transferred: int = 0
    transfer_failures: int = 0
    last_transfer_duration_ms: float = 0.0
    alpha: float = 0.25  # EWMA smoothing factor


class NetworkEstimator:
    """Estimates network transfer costs and predicts local vs remote execution time."""

    def __init__(self, alpha: float = 0.25) -> None:
        self.alpha = alpha
        self._metrics: Dict[str, NodeNetworkMetrics] = {}
        self._lock = asyncio.Lock()

    def get_or_create_metrics(self, node_id: str, is_local: bool = False) -> NodeNetworkMetrics:
        """Retrieves or initializes metrics for a node with conservative defaults."""
        if node_id not in self._metrics:
            if is_local:
                self._metrics[node_id] = NodeNetworkMetrics(
                    node_id=node_id,
                    rtt_ms_ewma=0.5,
                    upload_mbps_ewma=1000.0,
                    download_mbps_ewma=1000.0,
                    alpha=self.alpha,
                )
            else:
                self._metrics[node_id] = NodeNetworkMetrics(
                    node_id=node_id,
                    rtt_ms_ewma=20.0,
                    upload_mbps_ewma=40.0,
                    download_mbps_ewma=60.0,
                    alpha=self.alpha,
                )
        return self._metrics[node_id]

    def update_rtt(self, node_id: str, rtt_ms: float, is_local: bool = False) -> None:
        """Updates RTT EWMA for a node."""
        if rtt_ms <= 0:
            return
        m = self.get_or_create_metrics(node_id, is_local=is_local)
        m.rtt_ms_ewma = (1.0 - m.alpha) * m.rtt_ms_ewma + m.alpha * rtt_ms

    def update_transfer(
        self,
        node_id: str,
        bytes_transferred: int,
        duration_seconds: float,
        direction: str = "upload",
        is_local: bool = False,
    ) -> None:
        """Updates measured transfer speed and failure stats."""
        m = self.get_or_create_metrics(node_id, is_local=is_local)
        m.transfers_count += 1
        m.total_bytes_transferred += bytes_transferred
        duration_ms = max(0.001, duration_seconds * 1000.0)
        m.last_transfer_duration_ms = duration_ms

        if bytes_transferred > 0 and duration_seconds > 0.0001:
            mbps = (bytes_transferred * 8.0 / 1e6) / duration_seconds
            # Bound realistic bounds for Wi-Fi LAN
            mbps_bounded = max(0.5, min(mbps, 2000.0))
            if direction == "upload":
                m.upload_mbps_ewma = (1.0 - m.alpha) * m.upload_mbps_ewma + m.alpha * mbps_bounded
            else:
                m.download_mbps_ewma = (1.0 - m.alpha) * m.download_mbps_ewma + m.alpha * mbps_bounded

    def record_transfer_failure(self, node_id: str) -> None:
        m = self.get_or_create_metrics(node_id)
        m.transfer_failures += 1

    def estimate_upload_time_ms(self, bytes_count: int, node: Union[NodeProfile, str]) -> float:
        """Estimates upload duration in milliseconds."""
        node_id = node.id if isinstance(node, NodeProfile) else str(node)
        is_local = node.capabilities.is_local if isinstance(node, NodeProfile) else False

        if bytes_count <= 0:
            return 0.0
        if is_local:
            return 0.5  # Local memory copy / zero network overhead

        m = self.get_or_create_metrics(node_id, is_local=False)
        speed_mbps = max(0.5, m.upload_mbps_ewma)
        upload_ms = ((bytes_count * 8.0) / (speed_mbps * 1e6)) * 1000.0
        return round(upload_ms, 2)

    def estimate_download_time_ms(self, bytes_count: int, node: Union[NodeProfile, str]) -> float:
        """Estimates download duration in milliseconds."""
        node_id = node.id if isinstance(node, NodeProfile) else str(node)
        is_local = node.capabilities.is_local if isinstance(node, NodeProfile) else False

        if bytes_count <= 0:
            return 0.0
        if is_local:
            return 0.2

        m = self.get_or_create_metrics(node_id, is_local=False)
        speed_mbps = max(0.5, m.download_mbps_ewma)
        download_ms = ((bytes_count * 8.0) / (speed_mbps * 1e6)) * 1000.0
        return round(download_ms, 2)

    def estimate_inference_time_ms(self, task: Task, node: NodeProfile) -> float:
        """Estimates task computation time based on hardware capability and load."""
        is_ai = task.task_type in ("image_inference", "yolo", "ai_inference")
        has_gpu = node.capabilities.has_gpu

        if is_ai:
            if has_gpu:
                base_time = 28.0  # Fast GPU YOLO pass
            else:
                base_time = 135.0  # CPU YOLO pass
        else:
            base_time = 50.0

        # Adjust for performance multiplier
        adjusted = base_time / max(0.1, node.performance_multiplier)
        return round(adjusted, 2)

    def estimate_remote_execution_time(
        self,
        task: Task,
        node: NodeProfile,
        payload_size_bytes: int = 0,
    ) -> Dict[str, float]:
        """Calculates breakdown: T_remote = T_upload + T_rtt + T_queue + T_infer + T_download."""
        upload_ms = self.estimate_upload_time_ms(payload_size_bytes, node)
        m = self.get_or_create_metrics(node.id, is_local=node.capabilities.is_local)
        rtt_ms = round(m.rtt_ms_ewma, 2)

        # Queue / wait time based on node load
        active = node.telemetry.active_tasks if node.telemetry else 0
        queue_ms = round(active * 25.0, 2)

        inference_ms = self.estimate_inference_time_ms(task, node)
        download_ms = self.estimate_download_time_ms(1024, node)  # structured result ~1KB

        total = round(upload_ms + rtt_ms + queue_ms + inference_ms + download_ms, 2)

        return {
            "upload_ms": upload_ms,
            "rtt_ms": rtt_ms,
            "queue_wait_ms": queue_ms,
            "remote_inference_ms": inference_ms,
            "download_ms": download_ms,
            "total_remote_ms": total,
        }

    def estimate_local_execution_time(
        self,
        task: Task,
        local_node: Optional[NodeProfile],
        payload_size_bytes: int = 0,
    ) -> float:
        """Calculates local execution cost. Returns float('inf') if local node cannot run task."""
        if not local_node:
            return float("inf")

        # Check compatibility
        if task.requires_gpu and not local_node.capabilities.has_gpu:
            return float("inf")
        if local_node.capabilities.supported_handlers and task.task_type not in local_node.capabilities.supported_handlers:
            return float("inf")

        active = local_node.telemetry.active_tasks if local_node.telemetry else 0
        queue_ms = active * 25.0
        inference_ms = self.estimate_inference_time_ms(task, local_node)
        return round(queue_ms + inference_ms, 2)

    def compare_local_vs_remote(
        self,
        task: Task,
        local_node: Optional[NodeProfile],
        remote_node: NodeProfile,
        payload_size_bytes: int = 0,
    ) -> Dict[str, Any]:
        """Evaluates whether to offload to remote node or execute locally."""
        remote_details = self.estimate_remote_execution_time(task, remote_node, payload_size_bytes)
        remote_total = remote_details["total_remote_ms"]

        local_total = self.estimate_local_execution_time(task, local_node, payload_size_bytes)

        if local_node is None:
            return {
                "decision": "remote",
                "reason": "no local node available",
                "local_estimate_ms": None,
                "remote_estimate_ms": remote_total,
                "remote_details": remote_details,
            }

        if local_total == float("inf"):
            return {
                "decision": "remote",
                "reason": "local node incapable of running task requirements",
                "local_estimate_ms": None,
                "remote_estimate_ms": remote_total,
                "remote_details": remote_details,
            }

        if remote_total < local_total:
            return {
                "decision": "remote",
                "reason": f"remote execution predicted faster ({remote_total}ms < {local_total}ms)",
                "local_estimate_ms": local_total,
                "remote_estimate_ms": remote_total,
                "remote_details": remote_details,
            }
        else:
            return {
                "decision": "local",
                "reason": f"local execution predicted faster or equal ({local_total}ms <= {remote_total}ms)",
                "local_estimate_ms": local_total,
                "remote_estimate_ms": remote_total,
                "remote_details": remote_details,
            }
