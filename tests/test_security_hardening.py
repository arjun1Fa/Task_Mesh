"""Automated Security Hardening Test Suite for TaskMesh.

Tests RBAC enforcement, session persistence, WebSocket authentication,
Worker Console endpoint protection, Anti-CSRF/Host header validation,
Worker port collision resilience, and secure bootstrap credential generation.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
import socket
import tempfile
import time
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from taskmesh.core.config import NodeConfig, OrchestratorConfig
from taskmesh.core.enums import NodeStatus, TaskStatus
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task, TaskCreate
from taskmesh.node.agent import NodeAgent
from taskmesh.node.console_server import create_worker_console_app, start_console_server
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.orchestrator.server import create_app
from taskmesh.persistence.repositories import MemoryTaskRepository
from taskmesh.security.auth import AuthManager, TokenPayload, UserCreate, UserRole, UserUpdate, hash_password


@pytest.fixture
def temp_db_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def auth_fixture(temp_db_dir: str) -> AuthManager:
    db_path = os.path.join(temp_db_dir, "test_auth.db")
    return AuthManager(db_path=db_path, token_secret="test-token-secret-12345")


@pytest.fixture
def hardened_runtime(temp_db_dir: str) -> OrchestratorRuntime:
    db_path = os.path.join(temp_db_dir, "runtime.db")
    auth = AuthManager(db_path=db_path, token_secret="runtime-token-secret-xyz")
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(host="127.0.0.1", port=8000, join_token="cluster-join-token-secret")
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    rt.auth = auth
    return rt


@pytest.fixture
def test_client(hardened_runtime: OrchestratorRuntime) -> TestClient:
    app = create_app(runtime=hardened_runtime)
    return TestClient(app)


# ==============================================================================
# 1. Unauthenticated API Rejection
# ==============================================================================

def test_unauthenticated_api_rejection(test_client: TestClient):
    """Verifies that all privileged endpoints return 401 when called without credentials."""
    # POST endpoints
    endpoints_post = [
        ("/v1/tasks", {"task_type": "cpu_test", "payload": {}}),
        ("/v1/cluster/dispatch/pause", {}),
        ("/v1/scheduler/mode", {"mode": "fair"}),
        ("/v1/nodes/node-test/drain", {}),
        ("/v1/users", {"username": "u1", "password": "p1", "role": "viewer"}),
    ]
    for url, body in endpoints_post:
        resp = test_client.post(url, json=body)
        assert resp.status_code == 401, f"Expected 401 for POST {url}, got {resp.status_code}"
        assert "Authentication required" in resp.json().get("detail", "")

    # GET endpoints requiring authorization
    endpoints_get = [
        "/v1/tasks",
        "/v1/audit/logs",
        "/v1/dlq",
        "/v1/nodes",
        "/v1/scheduler/status",
        "/v1/system/config",
    ]
    for url in endpoints_get:
        resp = test_client.get(url)
        assert resp.status_code == 401, f"Expected 401 for GET {url}, got {resp.status_code}"

    # Unauthenticated /health liveness probe should succeed
    health_resp = test_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json().get("status") in ("ok", "healthy")


# ==============================================================================
# 2. Viewer Role Privilege Boundary
# ==============================================================================

def test_viewer_role_privilege_boundary(hardened_runtime: OrchestratorRuntime, test_client: TestClient):
    """Verifies that a VIEWER role can read cluster state but is rejected (403) on mutations."""
    # Create a viewer user
    viewer_user = hardened_runtime.auth.create_user(
        UserCreate(username="viewer_user", password="password123", role=UserRole.VIEWER)
    )
    assert viewer_user is not None
    auth_res = hardened_runtime.auth.authenticate("viewer_user", "password123")
    assert auth_res is not None
    _, viewer_token = auth_res

    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Allowed reads
    assert test_client.get("/v1/cluster/health", headers=headers).status_code == 200
    assert test_client.get("/v1/tasks", headers=headers).status_code == 200
    assert test_client.get("/v1/scheduler/status", headers=headers).status_code == 200
    assert test_client.get("/v1/nodes", headers=headers).status_code == 200

    # Disallowed mutations (403 Forbidden)
    r1 = test_client.post("/v1/tasks", json={"task_type": "cpu_test", "payload": {}}, headers=headers)
    assert r1.status_code == 403, f"Expected 403 for tasks.submit, got {r1.status_code}"

    r2 = test_client.post("/v1/cluster/dispatch/pause", headers=headers)
    assert r2.status_code == 403, f"Expected 403 for cluster.manage, got {r2.status_code}"

    r3 = test_client.post("/v1/scheduler/mode", json={"mode": "fair"}, headers=headers)
    assert r3.status_code == 403, f"Expected 403 for scheduler.configure, got {r3.status_code}"

    r4 = test_client.post("/v1/nodes/node-test/drain", headers=headers)
    assert r4.status_code == 403, f"Expected 403 for nodes.manage, got {r4.status_code}"

    r5 = test_client.post("/v1/users", json={"username": "hacker", "password": "p", "role": "viewer"}, headers=headers)
    assert r5.status_code == 403, f"Expected 403 for users.manage, got {r5.status_code}"


# ==============================================================================
# 3. Operator Role User Management Boundary
# ==============================================================================

def test_operator_role_user_management_boundary(hardened_runtime: OrchestratorRuntime, test_client: TestClient):
    """Verifies that an ORCHESTRATOR_OPERATOR can manage tasks/nodes but CANNOT manage users."""
    op_user = hardened_runtime.auth.create_user(
        UserCreate(username="cluster_op", password="password123", role=UserRole.ORCHESTRATOR_OPERATOR)
    )
    assert op_user is not None
    auth_res = hardened_runtime.auth.authenticate("cluster_op", "password123")
    assert auth_res is not None
    _, token = auth_res
    headers = {"Authorization": f"Bearer {token}"}

    # Operator can submit tasks
    r_task = test_client.post("/v1/tasks", json={"task_type": "cpu_test", "payload": {}}, headers=headers)
    assert r_task.status_code == 201

    # Operator cannot manage users
    r_user_create = test_client.post(
        "/v1/users",
        json={"username": "new_admin", "password": "pw", "role": "super_admin"},
        headers=headers,
    )
    assert r_user_create.status_code == 403

    r_user_update = test_client.patch(
        "/v1/users/admin",
        json={"password": "hacked_password"},
        headers=headers,
    )
    assert r_user_update.status_code == 403

    r_user_delete = test_client.delete("/v1/users/admin", headers=headers)
    assert r_user_delete.status_code == 403


# ==============================================================================
# 4. Worker Operator Node Scope Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_worker_operator_node_scope_isolation(hardened_runtime: OrchestratorRuntime, test_client: TestClient):
    """Verifies that a worker operator cannot view or manage nodes outside their assigned node scope."""
    # Register node-alpha and node-beta
    profile_alpha = NodeProfile(
        id="node-alpha",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(cpu_cores=4, worker_capacity=2, supported_handlers=["cpu_test"]),
    )
    profile_beta = NodeProfile(
        id="node-beta",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(cpu_cores=4, worker_capacity=2, supported_handlers=["cpu_test"]),
    )
    await hardened_runtime.registry.register(profile_alpha, None)
    await hardened_runtime.registry.register(profile_beta, None)

    # Create worker operator scoped strictly to node-alpha
    hardened_runtime.auth.create_user(
        UserCreate(username="op_alpha", password="password123", role=UserRole.WORKER_OPERATOR, node_scope="node-alpha")
    )
    auth_res = hardened_runtime.auth.authenticate("op_alpha", "password123")
    assert auth_res is not None
    _, token = auth_res
    headers = {"Authorization": f"Bearer {token}"}

    # Accessing scoped node-alpha succeeds
    r_alpha = test_client.get("/v1/worker/node-alpha/pool", headers=headers)
    assert r_alpha.status_code == 200
    assert r_alpha.json()["node_id"] == "node-alpha"

    # Accessing unscoped node-beta is forbidden (403)
    r_beta = test_client.get("/v1/worker/node-beta/pool", headers=headers)
    assert r_beta.status_code == 403
    assert "node scope mismatch" in r_beta.json()["detail"]


# ==============================================================================
# 5. Worker Console Unauthorized Mutations Rejection
# ==============================================================================

class DummyWorkerAgent:
    def __init__(self, node_id: str = "worker-hardening-01"):
        self.node_id = node_id
        self.status = NodeStatus.ONLINE
        self.config = NodeConfig(orchestrator_url="ws://127.0.0.1:8000/v1/ws/nodes", worker_concurrency=4)
        self.capabilities = NodeCapabilities(hostname="worker-box", cpu_cores=8, ram_total_mb=16384)
        self.pool = type("DummyPool", (), {
            "active_count": 0,
            "get_supported_handlers": lambda: ["cpu_test", "log"],
            "_semaphore": asyncio.Semaphore(4),
        })()
        self.rtt_ms_ewma = 12.5
        self.upload_mbps_ewma = 85.0
        self.download_mbps_ewma = 120.0
        self._seq_num = 1
        self._ws = None
        self.console_token = "valid-worker-console-token-999"


def test_worker_console_unauthorized_mutations():
    """Verifies that mutating worker console endpoints reject unauthenticated requests (401)."""
    agent = DummyWorkerAgent()
    app = create_worker_console_app(agent)
    client = TestClient(app)

    # Mutating requests without X-Worker-Token must return 401
    assert client.post("/api/worker/drain").status_code == 401
    assert client.post("/api/worker/resume").status_code == 401
    assert client.post("/api/worker/maintenance", json={"maintenance": True}).status_code == 401
    assert client.post("/api/worker/concurrency", json={"concurrency": 2}).status_code == 401
    assert client.post("/api/worker/pause_assignments").status_code == 401

    # Mutating requests with invalid token must return 401
    bad_headers = {"X-Worker-Token": "invalid-token-xyz"}
    assert client.post("/api/worker/drain", headers=bad_headers).status_code == 401


# ==============================================================================
# 6. Worker Console Authorized Loopback
# ==============================================================================

def test_worker_console_authorized_loopback():
    """Verifies that loopback callers can obtain the worker token and execute mutations."""
    agent = DummyWorkerAgent()
    app = create_worker_console_app(agent)
    client = TestClient(app)

    # Local loopback request to identity returns console_token
    r_ident = client.get("/api/worker/identity")
    assert r_ident.status_code == 200
    token = r_ident.json().get("console_token")
    assert token == agent.console_token

    # Using valid X-Worker-Token enables mutations
    headers = {"X-Worker-Token": token}

    r_drain = client.post("/api/worker/drain", headers=headers)
    assert r_drain.status_code == 200
    assert r_drain.json()["status"] == "draining"
    assert agent.status == NodeStatus.DRAINING

    r_resume = client.post("/api/worker/resume", headers=headers)
    assert r_resume.status_code == 200
    assert r_resume.json()["status"] == "online"
    assert agent.status == NodeStatus.ONLINE

    r_conc = client.post("/api/worker/concurrency", json={"concurrency": 8}, headers=headers)
    assert r_conc.status_code == 200
    assert agent.config.worker_concurrency == 8


# ==============================================================================
# 7. Worker Console CSRF & Host Validation
# ==============================================================================

def test_worker_console_csrf_and_host_validation():
    """Verifies that requests from untrusted origins or with disallowed Host headers are rejected (403)."""
    agent = DummyWorkerAgent()
    app = create_worker_console_app(agent)
    client = TestClient(app)

    valid_token = agent.console_token

    # Malicious cross-origin request rejected (Anti-CSRF)
    csrf_headers = {
        "X-Worker-Token": valid_token,
        "Origin": "http://malicious-attacker-website.com",
    }
    r_csrf = client.post("/api/worker/drain", headers=csrf_headers)
    assert r_csrf.status_code == 403
    assert "Forbidden cross-origin" in r_csrf.json()["detail"]

    # DNS rebinding / invalid Host header rejected
    rebinding_headers = {
        "X-Worker-Token": valid_token,
        "Host": "attacker-controlled-host.com",
    }
    r_rebinding = client.post("/api/worker/drain", headers=rebinding_headers)
    assert r_rebinding.status_code == 403
    assert "Forbidden host header" in r_rebinding.json()["detail"]


# ==============================================================================
# 8. Dashboard WebSocket Authentication
# ==============================================================================

def test_dashboard_websocket_authentication(hardened_runtime: OrchestratorRuntime, test_client: TestClient):
    """Verifies that /v1/ws/dashboard enforces token authentication and rejects unauthenticated connections."""
    # 1. Unauthenticated connection is rejected with WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with test_client.websocket_connect("/v1/ws/dashboard"):
            pass
    assert exc_info.value.code == 1008

    # 2. Invalid token connection is rejected with WS 1008
    with pytest.raises(WebSocketDisconnect) as exc_info_invalid:
        with test_client.websocket_connect("/v1/ws/dashboard?token=bad-token"):
            pass
    assert exc_info_invalid.value.code == 1008

    # 3. Valid authenticated connection succeeds and receives initial sync
    hardened_runtime.auth.create_user(
        UserCreate(username="dash_viewer", password="password123", role=UserRole.VIEWER)
    )
    auth_res = hardened_runtime.auth.authenticate("dash_viewer", "password123")
    assert auth_res is not None
    _, valid_token = auth_res

    with test_client.websocket_connect(f"/v1/ws/dashboard?token={valid_token}") as ws:
        initial_msg = ws.receive_json()
        assert initial_msg["event_type"] == "initial_sync"
        assert "data" in initial_msg
        assert "online_nodes" in initial_msg["data"]


# ==============================================================================
# 9. Worker Port Collision Recovery
# ==============================================================================

@pytest.mark.asyncio
async def test_worker_port_collision_recovery():
    """Verifies that if the console port is already in use, NodeAgent survives and sets status to 'unavailable'."""
    # Bind a temporary socket to occupy a port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    occupied_port = sock.getsockname()[1]

    agent = DummyWorkerAgent()
    agent.console_status = "uninitialized"

    try:
        # Start console server on the occupied port
        # Must not raise an unhandled exception or crash the process
        await start_console_server(agent, port=occupied_port, host="127.0.0.1")
        assert agent.console_status == "unavailable"
    finally:
        sock.close()


# ==============================================================================
# 10. Admin Bootstrap Secret & Session Persistence
# ==============================================================================

def test_admin_bootstrap_secret_and_persistence(temp_db_dir: str):
    """Verifies random bootstrap secret generation, custom env pass override, session persistence, and revocation."""
    db_path = os.path.join(temp_db_dir, "bootstrap_test.db")
    secret_file = os.path.join(temp_db_dir, ".admin_bootstrap_secret")

    # Ensure no environment password is set
    os.environ.pop("TASKMESH_ADMIN_PASSWORD", None)

    # 1. Bootstrap generates secret file with random password
    auth1 = AuthManager(db_path=db_path)
    assert os.path.exists(secret_file), "Expected .admin_bootstrap_secret to be created"
    with open(secret_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TASKMESH_ADMIN_PASSWORD=" in content
    generated_pass = content.split("TASKMESH_ADMIN_PASSWORD=")[1].split("\n")[0].strip()
    assert len(generated_pass) >= 16

    # Admin user can authenticate with generated password
    auth_res1 = auth1.authenticate("admin", generated_pass)
    assert auth_res1 is not None
    _, token1 = auth_res1

    # 2. Re-instantiating AuthManager on same DB never resets existing admin password
    os.environ["TASKMESH_ADMIN_PASSWORD"] = "attempt_overwrite_pw"
    auth2 = AuthManager(db_path=db_path)
    assert auth2.authenticate("admin", generated_pass) is not None
    assert auth2.authenticate("admin", "attempt_overwrite_pw") is None
    os.environ.pop("TASKMESH_ADMIN_PASSWORD", None)

    # 3. Session persistence across AuthManager instances
    auth3 = AuthManager(db_path=db_path)
    # The previously issued token1 should still validate from SQLite session table
    payload = auth3.validate_token(token1)
    assert payload is not None
    assert payload.username == "admin"
    assert payload.role == UserRole.SUPER_ADMIN

    # 4. Token revocation
    auth3.revoke_token(token1)
    assert auth3.validate_token(token1) is None

    # 5. Revocation of all user sessions on password change
    auth_res2 = auth3.authenticate("admin", generated_pass)
    assert auth_res2 is not None
    _, token2 = auth_res2
    assert auth3.validate_token(token2) is not None

    auth3.update_user("admin", UserUpdate(password="brand_new_admin_password_999"))
    # Old token2 must now be revoked
    assert auth3.validate_token(token2) is None
    # Authentication with new password succeeds
    auth_res3 = auth3.authenticate("admin", "brand_new_admin_password_999")
    assert auth_res3 is not None
    _, token3 = auth_res3
    assert token3 is not None
