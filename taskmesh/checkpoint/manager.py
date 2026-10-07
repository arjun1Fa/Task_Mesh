"""Checkpoint management for tasks that declare checkpoint capabilities."""

import asyncio
from typing import Dict, Optional

from taskmesh.core.models import CheckpointData, Task


class CheckpointManager:
    """Stores latest checkpoint state per task for fault recovery."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._checkpoints: Dict[str, CheckpointData] = {}

    async def save_checkpoint(self, checkpoint: CheckpointData) -> None:
        async with self._lock:
            self._checkpoints[checkpoint.task_id] = checkpoint

    async def get_latest_checkpoint(self, task_id: str) -> Optional[CheckpointData]:
        async with self._lock:
            return self._checkpoints.get(task_id)

    async def attach_checkpoint(self, task: Task) -> None:
        """Attaches the latest recorded checkpoint state to task if present."""
        async with self._lock:
            cp = self._checkpoints.get(task.id)
            if cp:
                task.latest_checkpoint = cp

    async def clear_checkpoint(self, task_id: str) -> None:
        async with self._lock:
            self._checkpoints.pop(task_id, None)
