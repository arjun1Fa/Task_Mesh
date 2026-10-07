"""Test demonstrating persistent recovery across Orchestrator restart."""

import gc
import os
import tempfile
import pytest

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import CheckpointData, TaskCreate, TaskResult
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import SQLiteTaskRepository


@pytest.mark.asyncio
async def test_orchestrator_restart_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        cfg = OrchestratorConfig(db_url=f"sqlite:///{db_path}")
        
        # 1. Start Orchestrator Instance 1
        repo_1 = SQLiteTaskRepository(db_path)
        runtime_1 = OrchestratorRuntime(repository=repo_1, config=cfg)
        await runtime_1.start()

        # Submit tasks
        task_1 = await runtime_1.submit_task(
            TaskCreate(
                task_type="log",
                payload={"msg": "persisted-task-1"},
                priority=10,
                idempotency_key="key-persisted-1",
            )
        )
        task_2 = await runtime_1.submit_task(
            TaskCreate(
                task_type="cpu_test",
                payload={"iterations": 500},
                priority=5,
                idempotency_key="key-persisted-2",
            )
        )

        # Record a checkpoint on task 2 and mark it running
        cp = CheckpointData(task_id=task_2.id, attempt_id="att-1", step=42, state={"progress": "halfway"})
        await runtime_1.checkpoints.save_checkpoint(cp)
        task_2.latest_checkpoint = cp
        task_2.status = TaskStatus.RUNNING
        await repo_1.save(task_2)

        # 2. Stop Orchestrator Instance 1 (simulate restart/shutdown)
        await runtime_1.stop()
        del runtime_1
        del repo_1
        gc.collect()

        # 3. Start completely new Orchestrator Instance 2 pointing to same SQLite database
        repo_2 = SQLiteTaskRepository(db_path)
        runtime_2 = OrchestratorRuntime(repository=repo_2, config=cfg)
        await runtime_2.start()

        # 4. Verify state restored:
        # task_1 remains PENDING
        restored_t1 = await repo_2.get(task_1.id)
        assert restored_t1 is not None
        assert restored_t1.payload["msg"] == "persisted-task-1"
        assert restored_t1.priority == 10
        assert restored_t1.idempotency_key == "key-persisted-1"

        # task_2 was recovered from RUNNING to PENDING by orchestrator startup recovery,
        # with its checkpoint intact!
        restored_t2 = await repo_2.get(task_2.id)
        assert restored_t2 is not None
        assert restored_t2.status == TaskStatus.PENDING
        assert restored_t2.latest_checkpoint is not None
        assert restored_t2.latest_checkpoint.step == 42
        assert restored_t2.latest_checkpoint.state["progress"] == "halfway"

        # 5. Verify system continues: complete task 2
        restored_t2.status = TaskStatus.COMPLETED
        restored_t2.result = TaskResult(
            task_id=restored_t2.id,
            attempt_id="att-1",
            node_id="node-restored",
            status=TaskStatus.COMPLETED,
            output={"done": True},
            execution_time_seconds=0.1,
        )
        await repo_2.save(restored_t2)

        final_t2 = await repo_2.get(task_2.id)
        assert final_t2.status == TaskStatus.COMPLETED

        await runtime_2.stop()
        del runtime_2
        del repo_2
        gc.collect()

    finally:
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
