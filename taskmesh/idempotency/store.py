"""Idempotency store to prevent duplicate task submissions."""

import asyncio
from typing import Dict, Optional


class IdempotencyStore:
    """Thread-safe and coroutine-safe in-memory idempotency store."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._entries: Dict[str, str] = {}  # key -> task_id

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            return self._entries.get(key)

    async def set_if_absent(self, key: str, task_id: str) -> bool:
        """Returns True if the key was newly recorded, False if key already exists."""
        async with self._lock:
            if key in self._entries:
                return False
            self._entries[key] = task_id
            return True

    async def remove(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()
