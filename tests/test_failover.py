"""Unit and integration tests for Primary / Standby Orchestrator replication and failover."""

import asyncio
import pytest

from taskmesh.checkpoint.manager import CheckpointManager
from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import (
    CheckpointData,
    NodeCapabilities,
    NodeProfile,
    Task,
    TaskCreate,
)
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import MemoryTaskRepository


@pytest.mark.asyncio
async def test_snapshot_creation_and_application():
    repo_pri = MemoryTaskRepository()
    cfg_pri = OrchestratorConfig(standby_mode=False)
    primary = OrchestratorRuntime(repository=repo_pri, config=cfg_pri)
    await primary.start()

    # 1. Add tasks, nodes, checkpoints, and weights on primary
    t1 = await primary.submit_task(TaskCreate(task_type="log", payload={"msg": "replicate me"}, priority=10))
    n1 = NodeProfile(id="node-pri-1", base_score=2.5)
    primary.registry._nodes[n1.id] = n1
    cp1 = CheckpointData(task_id=t1.id, attempt_id=f"{t1.id}-A1", step=42, state={"cursor": 100})
    await primary.checkpoints.save_checkpoint(cp1)

    # 2. Create snapshot
    snapshot = await primary.create_snapshot()
    assert len(snapshot["tasks"]) == 1
    assert len(snapshot["nodes"]) == 1
    assert len(snapshot["checkpoints"]) == 1
    assert snapshot["tasks"][0]["id"] == t1.id

    # 3. Create standby orchestrator and apply snapshot
    repo_sb = MemoryTaskRepository()
    cfg_sb = OrchestratorConfig(standby_mode=True)
    standby = OrchestratorRuntime(repository=repo_sb, config=cfg_sb)
    await standby.start()

    assert standby.config.standby_mode is True
    assert len(standby._background_tasks) == 1  # Only standby replicator running

    await standby.apply_snapshot(snapshot)

    # Verify state transferred to standby
    t1_sb = await standby.repo.get(t1.id)
    assert t1_sb is not None
    assert t1_sb.id == t1.id

    n1_sb = await standby.registry.get_node("node-pri-1")
    assert n1_sb is not None
    assert n1_sb.base_score == 2.5

    cp1_sb = await standby.checkpoints.get_latest_checkpoint(t1.id)
    assert cp1_sb is not None
    assert cp1_sb.step == 42

    # 4. Promote standby to primary
    await standby.promote_to_primary()
    assert standby.config.standby_mode is False
    assert len(standby._background_tasks) == 4  # All 4 dispatcher/health/lease loops started

    # Verify task was recovered into queue
    queued_task = await standby.queue.dequeue(timeout_seconds=0.1)
    assert queued_task is not None
    assert queued_task.id == t1.id

    await primary.stop()
    await standby.stop()
