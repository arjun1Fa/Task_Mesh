"""Tests for Stale Lease Protection, Late Result Rejection, Idempotency, and Node Draining."""

import asyncio
from datetime import datetime, timezone
import pytest

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import MessageType, NodeStatus, TaskStatus
from taskmesh.core.models import (
    NodeCapabilities,
    NodeProfile,
    Task,
    TaskCreate,
    TaskResult,
    utc_now,
)
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import MemoryTaskRepository
from taskmesh.protocol.messages import (
    ProtocolMessage,
    TaskCompletedPayload,
)


class MockWebSocket:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.sent_messages = []

    async def send(self, data: str) -> None:
        self.sent_messages.append(data)


@pytest.mark.asyncio
async def test_stale_lease_and_late_result_rejection():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(heartbeat_interval_seconds=1.0)
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    await rt.start()

    ws = MockWebSocket("node-1")
    n1 = NodeProfile(id="node-1", capabilities=NodeCapabilities(supported_handlers=["log"]))
    await rt.registry.register(n1, ws)

    # 1. Create task and assign attempt 1
    task = await rt.submit_task(TaskCreate(task_type="log", payload={"msg": "test"}))
    attempt1 = task.next_attempt("node-1", lease_duration_seconds=1.0)
    await rt.repo.save(task)

    # 2. Simulate task lease expiring and task reassigned to attempt 2
    attempt2 = task.next_attempt("node-2", lease_duration_seconds=5.0)
    await rt.repo.save(task)
    assert task.current_attempt_id == attempt2

    # 3. Old node returns late result for attempt 1
    late_res = TaskResult(
        task_id=task.id,
        attempt_id=attempt1,  # Stale attempt!
        node_id="node-1",
        status=TaskStatus.COMPLETED,
        output={"stale": True},
        execution_time_seconds=1.0,
    )
    late_msg = ProtocolMessage(
        message_type=MessageType.TASK_COMPLETED,
        node_id="node-1",
        payload=TaskCompletedPayload(
            task_id=task.id,
            attempt_id=attempt1,
            node_id="node-1",
            result=late_res,
        ).model_dump(mode="json"),
    )

    # Process late message
    import json
    await rt.handle_node_message(ws, json.dumps(late_msg.model_dump(mode="json")))

    # Verify task state was NOT overwritten by the stale result!
    current = await rt.repo.get(task.id)
    assert current.status == TaskStatus.RUNNING  # Still running attempt 2!
    assert current.result is None  # Stale result discarded!

    await rt.stop()


@pytest.mark.asyncio
async def test_idempotency_duplicate_submission():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(heartbeat_interval_seconds=1.0)
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    await rt.start()

    # Submit task with idempotency key
    req = TaskCreate(
        task_type="log",
        payload={"idemp": True},
        idempotency_key="unique-client-key-12345",
    )
    t1 = await rt.submit_task(req)

    # Submit identical task with same idempotency key
    t2 = await rt.submit_task(req)

    # Must return exact same task without duplicate queueing
    assert t1.id == t2.id

    tasks = await rt.repo.list()
    assert len(tasks) == 1

    await rt.stop()


@pytest.mark.asyncio
async def test_node_draining():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(heartbeat_interval_seconds=1.0)
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    await rt.start()

    ws = MockWebSocket("node-drain")
    n = NodeProfile(id="node-drain", capabilities=NodeCapabilities(supported_handlers=["log"]))
    await rt.registry.register(n, ws)

    # Drain node
    await rt.drain_node("node-drain")
    updated = await rt.registry.get_node("node-drain")
    assert updated.status == NodeStatus.DRAINING

    # Verify Draining node is excluded from eligibility
    from taskmesh.scheduler.base import filter_eligible_nodes
    task = Task(task_type="log")
    eligible = filter_eligible_nodes(task, [updated])
    assert len(eligible) == 0  # Draining nodes never receive new tasks

    await rt.stop()
