"""Dead-Letter Queue (DLQ) manager for exhausted or permanently failed tasks."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import Task, utc_now


class DLQItem(BaseModel):
    task: Task
    failed_at: datetime = Field(default_factory=utc_now)
    final_error: str
    failure_count: int


class DLQManager:
    """Manages poisoned and exhausted tasks that cannot be retried."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._items: Dict[str, DLQItem] = {}

    async def add(self, task: Task, final_error: str) -> None:
        async with self._lock:
            task.status = TaskStatus.DLQ
            task.error_message = final_error
            self._items[task.id] = DLQItem(
                task=task,
                final_error=final_error,
                failure_count=task.retry_count,
            )

    async def list_items(self) -> List[DLQItem]:
        async with self._lock:
            return list(self._items.values())

    async def get_item(self, task_id: str) -> Optional[DLQItem]:
        async with self._lock:
            return self._items.get(task_id)

    async def recover(self, task_id: str) -> Optional[Task]:
        """Recovers a task from DLQ, resetting attempt counter so it can be re-executed."""
        async with self._lock:
            item = self._items.pop(task_id, None)
            if not item:
                return None
            task = item.task
            task.status = TaskStatus.PENDING
            task.retry_count = 0
            task.error_message = None
            task.assigned_node_id = None
            task.active_lease = None
            task.updated_at = utc_now()
            return task

    async def purge(self) -> int:
        async with self._lock:
            count = len(self._items)
            self._items.clear()
            return count
