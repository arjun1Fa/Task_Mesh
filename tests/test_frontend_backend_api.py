"""Comprehensive tests for new control plane, auth, RBAC, audit, and worker console APIs."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import NodeStatus, SchedulerMode, TaskStatus
from taskmesh.core.models import NodeCapabilities, NodeProfile, TaskCreate
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.orchestrator.server import create_app
from taskmesh.persistence.repositories import MemoryTaskRepository
from taskmesh.security.auth import UserRole


@pytest_asyncio.fixture
async def app_and_runtime(tmp_path):
    db_file = str(tmp_path / "test_api.db")
    cfg = OrchestratorConfig(db_url=f"sqlite:///{db_file}")
    repo = MemoryTaskRepository()
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    app = create_app(runtime=rt, config=cfg)
    async with rt.repo._lock:
        pass
    yield app, rt
    await rt.stop()


@pytest.mark.asyncio
async def test_auth_bootstrap_and_login(app_and_runtime):
    app, rt = app_and_runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Default bootstrap user 'admin'
        res = await client.post("/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert res.status_code == 401

        res = await client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "super_admin"
        assert "token" in data
        assert "*" in data["permissions"]
        token = data["token"]

        # Validate me
        me_res = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["user"]["username"] == "admin"


@pytest.mark.asyncio
async def test_rbac_roles_and_permissions(app_and_runtime):
    app, rt = app_and_runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login as admin
        admin_login = await client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})
        admin_token = admin_login.json()["token"]

        # Admin creates viewer user
        res = await client.post(
            "/v1/users",
            json={"username": "viewer_user", "password": "viewpass123", "role": "viewer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 201
        assert res.json()["role"] == "viewer"

        # Login as viewer
        viewer_login = await client.post("/v1/auth/login", json={"username": "viewer_user", "password": "viewpass123"})
        viewer_token = viewer_login.json()["token"]

        # Viewer can view cluster health
        health_res = await client.get("/v1/cluster/health", headers={"Authorization": f"Bearer {viewer_token}"})
        assert health_res.status_code == 200

        # Viewer cannot manage users (403 Forbidden)
        forbidden_res = await client.post(
            "/v1/users",
            json={"username": "new_user", "password": "pwd", "role": "viewer"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert forbidden_res.status_code == 403


@pytest.mark.asyncio
async def test_master_controls_dispatch_pause_resume(app_and_runtime):
    app, rt = app_and_runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Initial status
        res = await client.get("/v1/cluster/dispatch/status")
        assert res.status_code == 200
        assert res.json()["dispatch_paused"] is False

        # Pause dispatch
        pause_res = await client.post("/v1/cluster/dispatch/pause")
        assert pause_res.status_code == 200
        assert pause_res.json()["dispatch_paused"] is True
        assert rt._dispatch_paused is True

        # Resume dispatch
        resume_res = await client.post("/v1/cluster/dispatch/resume")
        assert resume_res.status_code == 200
        assert resume_res.json()["dispatch_paused"] is False
        assert rt._dispatch_paused is False


@pytest.mark.asyncio
async def test_scheduler_diagnostics_and_mode_switch(app_and_runtime):
    app, rt = app_and_runtime
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get diagnostics
        diag_res = await client.get("/v1/scheduler/diagnostics")
        assert diag_res.status_code == 200
        data = diag_res.json()
        assert "mode" in data
        assert "mwu" in data
        assert "q_learning" in data
        assert "candidates" in data
        assert "wireless_estimator" in data

        # Switch mode to round robin
        switch_res = await client.post("/v1/scheduler/mode", json={"mode": "round_robin"})
        assert switch_res.status_code == 200
        assert switch_res.json()["new_mode"] == "round_robin"
        assert rt.config.scheduler_mode == SchedulerMode.ROUND_ROBIN

        # Switch back to adaptive
        switch_res2 = await client.post("/v1/scheduler/mode", json={"mode": "adaptive"})
        assert switch_res2.status_code == 200
        assert switch_res2.json()["new_mode"] == "adaptive"

        # Toggle adaptive stages
        toggle_res = await client.post("/v1/scheduler/toggles", json={"toggles": {"enable_mwu": False}})
        assert toggle_res.status_code == 200
        assert toggle_res.json()["toggles"]["enable_mwu"] is False


@pytest.mark.asyncio
async def test_node_extended_operations(app_and_runtime):
    app, rt = app_and_runtime
    # Manually register a node
    profile = NodeProfile(
        id="test-node-01",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            cpu_cores=8,
            cpu_frequency_mhz=3200,
            ram_total_mb=16384,
            ram_available_mb=12000,
            has_gpu=True,
            gpu_name="NVIDIA RTX 4090",
            gpu_vram_mb=24576,
            supported_handlers=["image_inference", "cpu_test"],
        ),
    )
    class DummyWS:
        pass
    await rt.registry.register(profile, DummyWS())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Maintenance mode
        maint_res = await client.post("/v1/nodes/test-node-01/maintenance", json={"maintenance": True})
        assert maint_res.status_code == 200
        assert maint_res.json()["status"] == "maintenance"

        # Resume node
        resume_res = await client.post("/v1/nodes/test-node-01/resume")
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "online"

        # Worker console endpoints for this node
        w_overview = await client.get("/v1/worker/test-node-01/overview")
        assert w_overview.status_code == 200
        assert w_overview.json()["node_id"] == "test-node-01"
        assert w_overview.json()["has_gpu"] is True

        w_hardware = await client.get("/v1/worker/test-node-01/hardware")
        assert w_hardware.status_code == 200
        assert w_hardware.json()["detected_hardware"]["cpu_cores"] == 8

        # Audit logs check
        audit_res = await client.get("/v1/audit/logs")
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) > 0

