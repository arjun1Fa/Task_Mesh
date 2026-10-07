"""Priority-aware task queue implementation with FIFO order stability."""

import asyncio
import heapq
from typing import List, Optional, Tuple

from taskmesh.core.models import Task


class PriorityQueue:
    """Async thread-safe priority queue.
    
    Higher priority integer tasks dequeue first.
    Ties are broken using FIFO sequence counter.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[int, int, Task]] = []
        self._counter: int = 0
        self._lock = asyncio.Lock()
        self._has_items = asyncio.Event()

    async def enqueue(self, task: Task) -> None:
        async with self._lock:
            # We negate priority because heapq is a min-heap, so highest priority gets smallest negative number
            heapq.heappush(self._heap, (-task.priority, self._counter, task))
            self._counter += 1
            self._has_items.set()

    async def dequeue(self, timeout_seconds: Optional[float] = None) -> Optional[Task]:
        """Dequeues the highest priority task, optionally waiting up to timeout_seconds."""
        while True:
            async with self._lock:
                if self._heap:
                    _, _, task = heapq.heappop(self._heap)
                    if not self._heap:
                        self._has_items.clear()
                    return task

            # Queue is empty, wait for items
            if timeout_seconds is not None and timeout_seconds <= 0:
                return None

            try:
                if timeout_seconds is not None:
                    await asyncio.wait_for(self._has_items.wait(), timeout=timeout_seconds)
                else:
                    await self._has_items.wait()
            except asyncio.TimeoutError:
                return None

    async def peek(self) -> Optional[Task]:
        async with self._lock:
            if not self._heap:
                return None
            return self._heap[0][2]

    async def len(self) -> int:
        async with self._lock:
            return len(self._heap)

    async def clear(self) -> None:
        async with self._lock:
            self._heap.clear()
            self._has_items.clear()
