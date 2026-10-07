"""Cluster node registry managing connected nodes and active WebSocket connections."""

import asyncio
from typing import Dict, List, Optional
import websockets

from taskmesh.core.enums import NodeStatus
from taskmesh.core.models import NodeProfile, NodeTelemetry, utc_now
from taskmesh.scoring.base_score import compute_base_score


class NodeRegistry:
    """Thread-safe registry for cluster compute nodes."""

    def __init__(self) -> None:
        self._nodes: Dict[str, NodeProfile] = {}
        self._sockets: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._lock = asyncio.Lock()

    async def register(self, profile: NodeProfile, websocket: websockets.WebSocketServerProtocol) -> None:
        async with self._lock:
            # If node re-registers, preserve historical stats if already present
            existing = self._nodes.get(profile.id)
            if existing:
                profile.base_score = existing.base_score
                profile.performance_multiplier = existing.performance_multiplier
                profile.drr_deficit = existing.drr_deficit
                profile.total_assigned = existing.total_assigned
                profile.total_completed = existing.total_completed
                profile.total_failed = existing.total_failed
            else:
                profile.base_score = compute_base_score(profile)

            profile.status = NodeStatus.ONLINE
            profile.last_heartbeat = utc_now()
            self._nodes[profile.id] = profile
            self._sockets[profile.id] = websocket

    async def unregister(self, node_id: str) -> None:
        async with self._lock:
            self._sockets.pop(node_id, None)
            if node_id in self._nodes:
                self._nodes[node_id].status = NodeStatus.OFFLINE

    async def get_node(self, node_id: str) -> Optional[NodeProfile]:
        async with self._lock:
            node = self._nodes.get(node_id)
            return node.model_copy() if node else None

    async def get_socket(self, node_id: str) -> Optional[websockets.WebSocketServerProtocol]:
        async with self._lock:
            return self._sockets.get(node_id)

    async def list_nodes(self, status: Optional[NodeStatus] = None) -> List[NodeProfile]:
        async with self._lock:
            nodes = list(self._nodes.values())
            if status:
                nodes = [n for n in nodes if n.status == status]
            return [n.model_copy() for n in nodes]

    async def update_heartbeat(self, node_id: str, status: Optional[NodeStatus] = None) -> None:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.last_heartbeat = utc_now()
                if status:
                    node.status = status
                elif node.status == NodeStatus.OFFLINE:
                    node.status = NodeStatus.ONLINE

    async def update_telemetry(self, node_id: str, telemetry: NodeTelemetry) -> None:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.telemetry = telemetry
                node.last_telemetry = utc_now()

    async def mark_offline(self, node_id: str) -> None:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.status = NodeStatus.OFFLINE
            self._sockets.pop(node_id, None)

    async def set_draining(self, node_id: str) -> None:
        async with self._lock:
            node = self._nodes.get(node_id)
            if node:
                node.status = NodeStatus.DRAINING
