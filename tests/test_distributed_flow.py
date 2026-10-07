"""End-to-end integration test of distributed task submission, execution, and failure recovery."""

import asyncio
import json
from typing import List
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
    HeartbeatPayload,
    ProtocolMessage,
    TaskCompletedPayload,
)


class MockWebSocket:
    """Mock WebSocket for deterministic in-memory integration testing."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.sent_messages: List[str] = []
        self.received_messages: List[str] = []
        self.is_closed = False

    async def send(self, data: str) -> None:
        self.sent_messages.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.is_closed = True


@pytest.mark.asyncio
async def test_distributed_task_flow_and_node_failure():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(
        heartbeat_interval_seconds=0.1,
        node_timeout_seconds=0.4,
        task_lease_seconds=5.0,
        scheduler_poll_seconds=0.05,
    )
    runtime = OrchestratorRuntime(repository=repo, config=cfg)
    await runtime.start()

    # 1. Register Node Alpha
    ws_alpha = MockWebSocket("node-alpha")
    profile_alpha = NodeProfile(
        id="node-alpha",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=4,
            supported_handlers=["log", "cpu_test"],
        ),
    )
    await runtime.registry.register(profile_alpha, ws_alpha)

    # 2. Submit task 1
    task1 = await runtime.submit_task(
        TaskCreate(
            task_type="log",
            payload={"message": "hello distributed TaskMesh"},
            priority=10,
        )
    )
    assert task1.status == TaskStatus.PENDING

    # Wait for dispatcher to assign task to node-alpha
    await asyncio.sleep(0.15)
    assert len(ws_alpha.sent_messages) >= 1

    assignment_raw = ws_alpha.sent_messages[-1]
    msg = ProtocolMessage.model_validate(json.loads(assignment_raw))
    assert msg.message_type == MessageType.TASK_ASSIGNMENT
    assert msg.payload["task_id"] == task1.id

    # 3. Simulate Node returning completed result for task 1
    result = TaskResult(
        task_id=task1.id,
        attempt_id=msg.payload["attempt_id"],
        node_id="node-alpha",
        status=TaskStatus.COMPLETED,
        output={"status": "success"},
        execution_time_seconds=0.05,
    )
    done_msg = ProtocolMessage(
        message_type=MessageType.TASK_COMPLETED,
        node_id="node-alpha",
        payload=TaskCompletedPayload(
            task_id=task1.id,
            attempt_id=msg.payload["attempt_id"],
            node_id="node-alpha",
            result=result,
        ).model_dump(mode="json"),
    )
    await runtime.handle_node_message(ws_alpha, json.dumps(done_msg.model_dump(mode="json")))

    # Verify task1 state in persistence is COMPLETED
    updated_task1 = await repo.get(task1.id)
    assert updated_task1 is not None
    assert updated_task1.status == TaskStatus.COMPLETED

    # 4. Refresh heartbeat for Node Alpha
    hb_msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-alpha",
        payload=HeartbeatPayload(node_id="node-alpha", sequence_number=1).model_dump(mode="json"),
    )
    await runtime.handle_node_message(ws_alpha, json.dumps(hb_msg.model_dump(mode="json")))

    # Submit task 2 while node is active
    task2 = await runtime.submit_task(
        TaskCreate(
            task_type="log",
            payload={"message": "task during node failure"},
            priority=5,
        )
    )
    await asyncio.sleep(0.15)
    t2_assigned = await repo.get(task2.id)
    assert t2_assigned.status == TaskStatus.RUNNING
    assert t2_assigned.assigned_node_id == "node-alpha"

    # 5. Stop sending heartbeats and wait for node timeout (> 0.4s)
    await asyncio.sleep(0.6)

    # Verify node-alpha is now detected OFFLINE
    node_state = await runtime.registry.get_node("node-alpha")
    assert node_state.status == NodeStatus.OFFLINE

    # Verify task2 was automatically recovered and re-queued
    t2_recovered = await repo.get(task2.id)
    assert t2_recovered.status == TaskStatus.PENDING
    assert t2_recovered.assigned_node_id is None

    await runtime.stop()
