"""Unit tests for WorkerPool concurrency, timeouts, and cancellation."""

import asyncio
from datetime import datetime, timezone
import pytest
from taskmesh.core.enums import TaskStatus
from taskmesh.node.worker_pool import WorkerPool
from taskmesh.protocol.messages import TaskAssignmentPayload


@pytest.mark.asyncio
async def test_worker_pool_execution():
    pool = WorkerPool(concurrency=2)

    async def sample_handler(payload, **kwargs):
        return {"val": payload["x"] * 2}

    pool.register_handler("double", sample_handler)

    assignment = TaskAssignmentPayload(
        task_id="t1",
        attempt_id="t1-A1",
        lease_id="l1",
        lease_expires_at=datetime.now(timezone.utc),
        task_type="double",
        payload={"x": 21},
        priority=0,
        timeout_seconds=5.0,
    )

    res = await pool.execute_assignment(assignment, node_id="node-1")
    assert res.status == TaskStatus.COMPLETED
    assert res.output == {"val": 42}
    assert res.execution_time_seconds >= 0.0


@pytest.mark.asyncio
async def test_worker_pool_timeout():
    pool = WorkerPool(concurrency=2)

    async def slow_handler(payload, **kwargs):
        await asyncio.sleep(2.0)
        return {"status": "ok"}

    pool.register_handler("slow", slow_handler)

    assignment = TaskAssignmentPayload(
        task_id="t2",
        attempt_id="t2-A1",
        lease_id="l2",
        lease_expires_at=datetime.now(timezone.utc),
        task_type="slow",
        payload={},
        priority=0,
        timeout_seconds=0.1,  # Strict timeout
    )

    res = await pool.execute_assignment(assignment, node_id="node-1")
    assert res.status == TaskStatus.FAILED
    assert "timed out" in res.error.lower()


@pytest.mark.asyncio
async def test_worker_pool_cancellation():
    pool = WorkerPool(concurrency=2)

    async def long_handler(payload, **kwargs):
        await asyncio.sleep(5.0)
        return {"done": True}

    pool.register_handler("long", long_handler)

    assignment = TaskAssignmentPayload(
        task_id="t3",
        attempt_id="t3-A1",
        lease_id="l3",
        lease_expires_at=datetime.now(timezone.utc),
        task_type="long",
        payload={},
        priority=0,
        timeout_seconds=10.0,
    )

    # Launch in background and cancel immediately
    task_coro = pool.execute_assignment(assignment, node_id="node-1")
    exec_task = asyncio.create_task(task_coro)
    await asyncio.sleep(0.05)

    cancelled = await pool.cancel_task("t3")
    assert cancelled is True

    res = await exec_task
    assert res.status == TaskStatus.CANCELLED
