"""Dashboard Event Hub for real-time WebSocket monitoring, event streaming, and logging."""

import asyncio
import json
import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
from pydantic import BaseModel, Field

from taskmesh.core.models import utc_now

logger = logging.getLogger("taskmesh.orchestrator.events")


class DashboardEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str  # e.g. "task.submitted", "task.assigned", "task.completed", "node.registered", "node.heartbeat"
    timestamp: datetime = Field(default_factory=utc_now)
    source: str = "orchestrator"
    entity_id: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class SystemLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:10]}")
    timestamp: datetime = Field(default_factory=utc_now)
    level: str  # "INFO", "WARNING", "ERROR", "DEBUG"
    source: str
    message: str
    task_id: Optional[str] = None
    node_id: Optional[str] = None


class DashboardEventHub:
    """Manages active browser WebSocket subscriptions and broadcasts cluster events."""

    def __init__(self, max_event_history: int = 500, max_log_history: int = 1000) -> None:
        self._sockets: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._event_history: deque[DashboardEvent] = deque(maxlen=max_event_history)
        self._log_history: deque[SystemLogEntry] = deque(maxlen=max_log_history)
        self._last_heartbeat_broadcast: Dict[str, float] = {}

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._sockets.add(websocket)
        logger.debug(f"Dashboard client connected. Active clients: {len(self._sockets)}")

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._sockets.discard(websocket)
        logger.debug(f"Dashboard client disconnected. Active clients: {len(self._sockets)}")

    async def broadcast(
        self,
        event_type: str,
        data: Dict[str, Any],
        entity_id: str = "",
        source: str = "orchestrator",
    ) -> DashboardEvent:
        """Broadcasts a structured event envelope to all connected dashboard clients."""
        event = DashboardEvent(
            event_type=event_type,
            source=source,
            entity_id=entity_id,
            data=data,
        )

        self._event_history.appendleft(event)

        if not self._sockets:
            return event

        msg_text = json.dumps(event.model_dump(mode="json"))
        dead_sockets: List[WebSocket] = []

        async with self._lock:
            for ws in list(self._sockets):
                try:
                    await ws.send_text(msg_text)
                except Exception:
                    dead_sockets.append(ws)

            for ws in dead_sockets:
                self._sockets.discard(ws)

        return event

    def log(
        self,
        level: str,
        source: str,
        message: str,
        task_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> SystemLogEntry:
        """Records a log entry into the live dashboard log stream."""
        entry = SystemLogEntry(
            level=level.upper(),
            source=source,
            message=message,
            task_id=task_id,
            node_id=node_id,
        )
        self._log_history.appendleft(entry)

        # Broadcast as event asynchronously if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(
                event_type="log.entry",
                data=entry.model_dump(mode="json"),
                entity_id=task_id or node_id or "",
                source=source,
            ))
        except RuntimeError:
            pass

        return entry

    def get_recent_events(self, limit: int = 100) -> List[DashboardEvent]:
        return list(self._event_history)[:limit]

    def get_recent_logs(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200,
    ) -> List[SystemLogEntry]:
        results = []
        search_lower = search.lower() if search else None
        for entry in self._log_history:
            if level and entry.level != level.upper():
                continue
            if source and entry.source != source:
                continue
            if search_lower and (search_lower not in entry.message.lower() and (not entry.task_id or search_lower not in entry.task_id.lower())):
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

