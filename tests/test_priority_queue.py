"""Unit tests for PriorityQueue ordering and FIFO tie-breaking."""

import pytest
from taskmesh.core.models import Task
from taskmesh.queue.priority import PriorityQueue


@pytest.mark.asyncio
async def test_priority_ordering():
    pq = PriorityQueue()
    t_low = Task(id="low", task_type="log", priority=1)
    t_med = Task(id="med", task_type="log", priority=5)
    t_high = Task(id="high", task_type="log", priority=10)

    await pq.enqueue(t_low)
    await pq.enqueue(t_high)
    await pq.enqueue(t_med)

    out1 = await pq.dequeue()
    out2 = await pq.dequeue()
    out3 = await pq.dequeue()

    assert out1.id == "high"
    assert out2.id == "med"
    assert out3.id == "low"


@pytest.mark.asyncio
async def test_fifo_tie_breaking():
    pq = PriorityQueue()
    t1 = Task(id="first", task_type="log", priority=5)
    t2 = Task(id="second", task_type="log", priority=5)

    await pq.enqueue(t1)
    await pq.enqueue(t2)

    out1 = await pq.dequeue()
    out2 = await pq.dequeue()

    assert out1.id == "first"
    assert out2.id == "second"
