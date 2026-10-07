"""Unit and integration tests for FastAPI REST endpoints."""

import pytest
import httpx
from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import TaskStatus
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.orchestrator.server import create_app
from taskmesh.persistence.repositories import MemoryTaskRepository


@pytest.mark.asyncio
async def test_rest_api_lifecycle():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(heartbeat_interval_seconds=1.0)
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    app = create_app(runtime=rt)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Cluster health check
        health_res = await client.get("/v1/cluster/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["scheduler_mode"] == "adaptive"

        # 2. Submit task
        task_payload = {
            "task_type": "cpu_test",
            "payload": {"iterations": 1000},
            "priority": 5,
        }
        post_res = await client.post("/v1/tasks", json=task_payload)
        assert post_res.status_code == 201
        created_task = post_res.json()
        task_id = created_task["id"]
        assert created_task["status"] == "pending"
        assert created_task["priority"] == 5

        # 3. Get task
        get_res = await client.get(f"/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == task_id

        # 4. List tasks
        list_res = await client.get("/v1/tasks")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 5. Cancel task
        cancel_res = await client.post(f"/v1/tasks/{task_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

        # 6. Retry cancelled task
        retry_res = await client.post(f"/v1/tasks/{task_id}/retry")
        assert retry_res.status_code == 200
        assert retry_res.json()["status"] == "pending"

        # 7. Scheduler status
        sched_res = await client.get("/v1/scheduler/status")
        assert sched_res.status_code == 200
        assert "mwu_weights" in sched_res.json()
