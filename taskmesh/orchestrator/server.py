"""FastAPI server and routes for the TaskMesh Orchestrator."""

from contextlib import asynccontextmanager
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import MessageType, NodeStatus, OffloadPolicy, SchedulerMode, TaskStatus

from taskmesh.core.errors import TaskNotFoundError
from taskmesh.core.models import NodeProfile, Task, TaskCreate, utc_now
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import SQLiteTaskRepository
from taskmesh.protocol.messages import (
    ProtocolMessage,
    RegisterAckPayload,
    RegisterNodePayload,
)
from taskmesh.security.auth import (
    TokenPayload,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
    PERMISSIONS_MAP,
)
from taskmesh.security.audit import AuditEvent

logger = logging.getLogger("taskmesh.server")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user: User
    token: str
    permissions: List[str]


class SchedulerModeRequest(BaseModel):
    mode: str


class SchedulerTogglesRequest(BaseModel):
    toggles: Dict[str, bool]


class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Any]


class NodeMaintenanceRequest(BaseModel):
    maintenance: bool


class ClusterHealthResponse(BaseModel):
    status: str
    total_nodes: int
    online_nodes: int
    total_tasks: int
    running_tasks: int
    pending_tasks: int
    dlq_tasks: int
    fairness_cv: float
    scheduler_mode: str


def create_app(
    runtime: Optional[OrchestratorRuntime] = None,
    config: Optional[OrchestratorConfig] = None,
) -> FastAPI:
    """Creates the FastAPI application for TaskMesh."""
    cfg = config or (runtime.config if runtime else OrchestratorConfig())
    rt = runtime or OrchestratorRuntime(
        repository=SQLiteTaskRepository(cfg.db_url.replace("sqlite:///", "")),
        config=cfg,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await rt.start()
        yield
        await rt.stop()

    app = FastAPI(
        title="TaskMesh Orchestrator",
        version="0.2.0",
        description="Lightweight distributed task orchestration and adaptive scheduling system",
        lifespan=lifespan,
    )

    configured_origins = os.getenv("TASKMESH_CORS_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in configured_origins if o.strip()]
    if not allowed_origins:
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            f"http://localhost:{cfg.port}",
            f"http://127.0.0.1:{cfg.port}",
        ]
        if cfg.host not in ("0.0.0.0", "127.0.0.1", "localhost"):
            allowed_origins.append(f"http://{cfg.host}:{cfg.port}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.runtime = rt

    # ---------------------------------------------------------
    # Authentication & RBAC Helper Functions
    # ---------------------------------------------------------

    def get_token_payload(request: Request) -> Optional[TokenPayload]:
        token = None
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
        elif "token" in request.query_params:
            token = request.query_params.get("token", "").strip()

        if not token:
            return None

        # Support cluster join_token as service token for internal nodes and recovery
        if token == rt.config.join_token:
            return TokenPayload(
                username="cluster-service",
                role=UserRole.SUPER_ADMIN,
                node_scope=None,
                permissions=sorted(list(PERMISSIONS_MAP[UserRole.SUPER_ADMIN])),
                exp=time.time() + 86400,
            )

        return rt.auth.validate_token(token)

    def require_permission(request: Request, permission: str) -> TokenPayload:
        payload = get_token_payload(request)
        if not payload:
            raise HTTPException(status_code=401, detail="Authentication required. Provide a valid Bearer token.")
        if not rt.auth.check_permission(payload, permission):
            rt.audit.log(
                action="permission.denied",
                actor=payload.username,
                role=payload.role.value,
                result="denied",
                details={"required_permission": permission},
            )
            raise HTTPException(status_code=403, detail=f"Permission denied: missing '{permission}'.")
        return payload

    # ---------------------------------------------------------
    # REST API Routes: Authentication & User Management
    # ---------------------------------------------------------

    @app.post("/v1/auth/login", response_model=LoginResponse)
    async def login(req: LoginRequest) -> LoginResponse:
        auth_res = rt.auth.authenticate(req.username, req.password)
        if not auth_res:
            rt.audit.log(action="auth.login", actor=req.username, result="denied", details={"reason": "Invalid credentials"})
            raise HTTPException(status_code=401, detail="Invalid username or password")
        user, token = auth_res
        perms = sorted(list(PERMISSIONS_MAP.get(user.role, set()))) if user.role != UserRole.SUPER_ADMIN else ["*"]
        rt.audit.log(action="auth.login", actor=user.username, role=user.role.value, result="success")
        return LoginResponse(user=user, token=token, permissions=perms)

    @app.post("/v1/auth/logout")
    async def logout(request: Request) -> Dict[str, str]:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
            payload = rt.auth.validate_token(token)
            if payload:
                rt.audit.log(action="auth.logout", actor=payload.username, role=payload.role.value, result="success")
            rt.auth.revoke_token(token)
        return {"status": "logged_out"}

    @app.get("/v1/auth/me")
    async def get_current_user_profile(request: Request) -> Dict[str, Any]:
        payload = get_token_payload(request)
        if not payload:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if payload.username == "cluster-service":
            service_user = User(
                id="service_admin",
                username="cluster-service",
                role=UserRole.SUPER_ADMIN,
                node_scope=None,
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            return {"user": service_user.model_dump(mode="json"), "permissions": ["*"]}
        user = rt.auth.get_user_by_username(payload.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        perms = sorted(list(PERMISSIONS_MAP.get(user.role, set()))) if user.role != UserRole.SUPER_ADMIN else ["*"]
        return {"user": user.model_dump(mode="json"), "permissions": perms}

    @app.get("/v1/auth/permissions")
    async def get_permissions_matrix() -> Dict[str, List[str]]:
        return {r.value: sorted(list(perms)) for r, perms in PERMISSIONS_MAP.items()}

    @app.get("/v1/users", response_model=List[User])
    async def list_users(request: Request) -> List[User]:
        require_permission(request, "users.view")
        return rt.auth.list_users()

    @app.post("/v1/users", response_model=User, status_code=201)
    async def create_user(req: UserCreate, request: Request) -> User:
        actor_payload = require_permission(request, "users.manage")
        existing = rt.auth.get_user_by_username(req.username)
        if existing:
            raise HTTPException(status_code=400, detail=f"Username '{req.username}' already exists")
        created = rt.auth.create_user(req)
        rt.audit.log(
            action="user.create",
            actor=actor_payload.username,
            role=actor_payload.role.value,
            target=created.username,
            result="success",
            details={"assigned_role": req.role.value, "node_scope": req.node_scope},
        )
        return created

    @app.patch("/v1/users/{username}", response_model=User)
    async def update_user(username: str, req: UserUpdate, request: Request) -> User:
        actor_payload = require_permission(request, "users.manage")
        updated = rt.auth.update_user(username, req)
        if not updated:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        rt.audit.log(
            action="user.update",
            actor=actor_payload.username,
            role=actor_payload.role.value,
            target=username,
            result="success",
            details={"updated_fields": [k for k, v in req.model_dump(exclude_unset=True).items() if k != "password"]},
        )
        return updated

    @app.delete("/v1/users/{username}")
    async def delete_user(username: str, request: Request) -> Dict[str, str]:
        actor_payload = require_permission(request, "users.manage")
        if username == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete default admin user")
        deleted = rt.auth.delete_user(username)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        rt.audit.log(
            action="user.delete",
            actor=actor_payload.username,
            role=actor_payload.role.value,
            target=username,
            result="success",
        )
        return {"status": "deleted", "username": username}

    # ---------------------------------------------------------
    # REST API Routes: Audit & System Logs
    # ---------------------------------------------------------

    @app.get("/v1/audit/logs", response_model=List[AuditEvent])
    async def get_audit_logs(
        request: Request,
        actor: Optional[str] = Query(None),
        action: Optional[str] = Query(None),
        result: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=500),
    ) -> List[AuditEvent]:
        require_permission(request, "audit.view")
        return rt.audit.query(actor=actor, action=action, result=result, limit=limit)

    @app.get("/v1/system/logs")
    async def get_system_logs(
        request: Request,
        level: Optional[str] = Query(None),
        source: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(200, ge=1, le=1000),
    ) -> List[Any]:
        require_permission(request, "logs.view")
        return [entry.model_dump(mode="json") for entry in rt.events.get_recent_logs(level=level, source=source, search=search, limit=limit)]

    # ---------------------------------------------------------
    # REST API Routes: Tasks
    # ---------------------------------------------------------

    @app.post("/v1/tasks", response_model=Task, status_code=201)
    async def submit_task(req: TaskCreate, request: Request) -> Task:
        require_permission(request, "tasks.submit")
        return await rt.submit_task(req)

    @app.post("/v1/tasks/binary", response_model=Task, status_code=201)
    async def submit_binary_task(
        request: Request,
        task_type: str = Query("image_inference"),
        model: str = Query("yolov8n"),
        priority: int = Query(0),
        offload_policy: str = Query("wireless_allowed"),
        requires_gpu: bool = Query(False),
    ) -> Task:
        require_permission(request, "tasks.submit")
        content_type = request.headers.get("content-type", "")
        binary_data = b""
        if "multipart/form-data" in content_type:
            form = await request.form()
            file_item = form.get("file")
            if hasattr(file_item, "read"):
                binary_data = await file_item.read()
            elif isinstance(file_item, (bytes, bytearray)):
                binary_data = bytes(file_item)
        else:
            binary_data = await request.body()

        if not binary_data:
            raise HTTPException(status_code=400, detail="Missing binary payload data in request body")

        policy_val = OffloadPolicy(offload_policy) if offload_policy in OffloadPolicy._value2member_map_ else OffloadPolicy.WIRELESS_ALLOWED
        req = TaskCreate(
            task_type=task_type,
            payload={"model": model, "mime_type": content_type or "image/jpeg"},
            priority=priority,
            requires_gpu=requires_gpu,
            offload_policy=policy_val,
        )
        return await rt.submit_task(req, binary_data=binary_data)

    @app.get("/v1/tasks/{task_id}/payload")
    async def get_task_payload(task_id: str, request: Request) -> Response:
        require_permission(request, "tasks.view")
        payload_data = await rt.payload_store.get_payload(task_id)
        if not payload_data:
            raise HTTPException(status_code=404, detail=f"No binary payload found for task {task_id}")
        meta = await rt.payload_store.get_meta(task_id)
        media_type = meta.mime_type if meta else "application/octet-stream"
        return Response(content=payload_data, media_type=media_type)

    @app.get("/v1/tasks", response_model=List[Task])
    async def list_tasks(
        request: Request,
        status: Optional[TaskStatus] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ) -> List[Task]:
        require_permission(request, "tasks.view")
        return await rt.repo.list(status=status, limit=limit)

    @app.get("/v1/tasks/{task_id}", response_model=Task)
    async def get_task(task_id: str, request: Request) -> Task:
        require_permission(request, "tasks.view")
        t = await rt.repo.get(task_id)
        if not t:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return t

    @app.post("/v1/tasks/{task_id}/cancel", response_model=Task)
    async def cancel_task(task_id: str, request: Request, reason: str = "Client cancellation") -> Task:
        require_permission(request, "tasks.cancel")
        try:
            return await rt.cancel_task(task_id, reason=reason)
        except TaskNotFoundError:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    @app.post("/v1/tasks/{task_id}/retry", response_model=Task)
    async def retry_task(task_id: str, request: Request) -> Task:
        require_permission(request, "tasks.retry")
        try:
            return await rt.retry_task(task_id)
        except TaskNotFoundError:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # ---------------------------------------------------------
    # REST API Routes: Nodes & Cluster
    # ---------------------------------------------------------

    @app.get("/v1/nodes", response_model=List[NodeProfile])
    async def list_nodes(request: Request, status: Optional[NodeStatus] = Query(None)) -> List[NodeProfile]:
        require_permission(request, "nodes.view")
        return await rt.registry.list_nodes(status=status)

    @app.get("/v1/nodes/{node_id}", response_model=NodeProfile)
    async def get_node(node_id: str, request: Request) -> NodeProfile:
        require_permission(request, "nodes.view")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return n

    @app.post("/v1/nodes/{node_id}/drain")
    async def drain_node(node_id: str, request: Request) -> Dict[str, str]:
        actor_payload = require_permission(request, "nodes.manage")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        await rt.drain_node(node_id, actor=actor_payload.username)
        return {"status": "draining", "node_id": node_id}

    @app.get("/health")
    async def health_ping() -> Dict[str, str]:
        return {"status": "ok"}

    async def get_cluster_health() -> ClusterHealthResponse:
        nodes = await rt.registry.list_nodes()
        online_nodes = [n for n in nodes if n.status == NodeStatus.ONLINE]
        all_tasks = await rt.repo.list(limit=2000)
        running = [t for t in all_tasks if t.status == TaskStatus.RUNNING]
        pending = [t for t in all_tasks if t.status == TaskStatus.PENDING]
        dlq_items = await rt.dlq.list_items()
        fairness = await rt.get_fairness_metric()

        return ClusterHealthResponse(
            status="healthy" if online_nodes else "no_online_nodes",
            total_nodes=len(nodes),
            online_nodes=len(online_nodes),
            total_tasks=len(all_tasks),
            running_tasks=len(running),
            pending_tasks=len(pending),
            dlq_tasks=len(dlq_items),
            fairness_cv=fairness,
            scheduler_mode=rt.config.scheduler_mode.value,
        )

    @app.get("/v1/cluster/health", response_model=ClusterHealthResponse)
    async def cluster_health(request: Request) -> ClusterHealthResponse:
        require_permission(request, "cluster.view")
        return await get_cluster_health()

    # ---------------------------------------------------------
    # REST API Routes: Scheduler & Explainability
    # ---------------------------------------------------------

    @app.get("/v1/scheduler/status")
    async def scheduler_status(request: Request) -> Dict[str, Any]:
        require_permission(request, "scheduler.view")
        resp: Dict[str, Any] = {
            "mode": rt.config.scheduler_mode.value,
            "fairness_cv": await rt.get_fairness_metric(),
            "wireless_metrics": {
                nid: m.model_dump(mode="json")
                for nid, m in rt.network_estimator._metrics.items()
            },
        }
        from taskmesh.scheduler.adaptive import AdaptiveScheduler
        if isinstance(rt.scheduler, AdaptiveScheduler):
            resp["mwu_weights"] = rt.scheduler.mwu.get_weights()
            resp["q_table_entries"] = len(rt.scheduler.rl.q_table)
            resp["rl_epsilon"] = rt.scheduler.rl.epsilon
        return resp

    @app.get("/v1/scheduler/decisions")
    async def scheduler_decisions(request: Request, limit: int = Query(50, ge=1, le=200)) -> List[Any]:
        require_permission(request, "scheduler.view")
        return await rt.get_decisions(limit=limit)

    @app.get("/v1/scheduler/diagnostics")
    async def get_scheduler_diagnostics(request: Request) -> Dict[str, Any]:
        require_permission(request, "scheduler.view")
        return await rt.get_scheduler_diagnostics()

    @app.post("/v1/scheduler/mode")
    async def change_scheduler_mode(req: SchedulerModeRequest, request: Request) -> Dict[str, str]:
        actor_payload = require_permission(request, "scheduler.configure")
        actor = actor_payload.username
        try:
            mode_enum = SchedulerMode(req.mode.lower())
        except ValueError:
            valid_modes = [m.value for m in SchedulerMode]
            raise HTTPException(status_code=400, detail=f"Invalid mode '{req.mode}'. Choose from: {valid_modes}")
        await rt.switch_scheduler_mode(mode_enum, actor=actor)
        return {"status": "switched", "new_mode": mode_enum.value}

    @app.post("/v1/scheduler/toggles")
    async def update_adaptive_toggles(req: SchedulerTogglesRequest, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "scheduler.configure")
        actor = actor_payload.username
        try:
            updated = await rt.set_adaptive_toggles(req.toggles, actor=actor)
            return {"status": "updated", "toggles": updated}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ---------------------------------------------------------
    # REST API Routes: Master Controls & Dispatch Management
    # ---------------------------------------------------------

    @app.get("/v1/cluster/dispatch/status")
    async def get_dispatch_status(request: Request) -> Dict[str, Any]:
        require_permission(request, "cluster.view")
        return {"dispatch_paused": rt._dispatch_paused}

    @app.post("/v1/cluster/dispatch/pause")
    async def pause_dispatch(request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "cluster.manage")
        actor = actor_payload.username
        await rt.set_dispatch_paused(True, actor=actor)
        return {"status": "paused", "dispatch_paused": True}

    @app.post("/v1/cluster/dispatch/resume")
    async def resume_dispatch(request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "cluster.manage")
        actor = actor_payload.username
        await rt.set_dispatch_paused(False, actor=actor)
        return {"status": "resumed", "dispatch_paused": False}

    # ---------------------------------------------------------
    # REST API Routes: Extended Node Management
    # ---------------------------------------------------------

    @app.post("/v1/nodes/{node_id}/resume")
    async def resume_node(node_id: str, request: Request) -> Dict[str, str]:
        actor_payload = require_permission(request, "nodes.manage")
        actor = actor_payload.username
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        await rt.resume_node(node_id, actor=actor)
        return {"status": "online", "node_id": node_id}

    @app.post("/v1/nodes/{node_id}/maintenance")
    async def set_node_maintenance(node_id: str, req: NodeMaintenanceRequest, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "nodes.manage")
        actor = actor_payload.username
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        await rt.set_node_maintenance(node_id, is_maint=req.maintenance, actor=actor)
        return {"status": "maintenance" if req.maintenance else "online", "node_id": node_id}

    @app.delete("/v1/nodes/{node_id}")
    async def delete_node(node_id: str, request: Request, force: bool = Query(False)) -> Dict[str, str]:
        actor_payload = require_permission(request, "nodes.manage")
        actor = actor_payload.username
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        try:
            await rt.remove_node(node_id, force=force, actor=actor)
            return {"status": "removed", "node_id": node_id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        try:
            await rt.remove_node(node_id, force=force, actor=actor)
            return {"status": "removed", "node_id": node_id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/v1/nodes/{node_id}/tasks", response_model=List[Task])
    async def get_node_tasks(node_id: str, request: Request, limit: int = Query(50, ge=1, le=200)) -> List[Task]:
        require_permission(request, "tasks.view")
        return await rt.get_node_tasks(node_id, limit=limit)

    # ---------------------------------------------------------
    # REST API Routes: System Config & Health
    # ---------------------------------------------------------

    @app.get("/v1/system/config")
    async def get_system_config(request: Request) -> Dict[str, Any]:
        require_permission(request, "system.view")
        return {
            "host": rt.config.host,
            "port": rt.config.port,
            "scheduler_mode": rt.config.scheduler_mode.value,
            "heartbeat_interval_seconds": rt.config.heartbeat_interval_seconds,
            "node_timeout_seconds": rt.config.node_timeout_seconds,
            "task_lease_seconds": rt.config.task_lease_seconds,
            "scheduler_poll_seconds": rt.config.scheduler_poll_seconds,
            "ewma_alpha": rt.config.ewma_alpha,
            "mwu_eta": rt.config.mwu_eta,
            "rl_learning_rate": rt.config.rl_learning_rate,
            "rl_discount_factor": rt.config.rl_discount_factor,
            "rl_epsilon": rt.config.rl_epsilon,
            "secure_mode": rt.config.secure_mode,
            "standby_mode": rt.config.standby_mode,
            "primary_url": rt.config.primary_url,
            "max_payload_size_bytes": rt.config.max_payload_size_bytes,
            "chunk_size_bytes": rt.config.chunk_size_bytes,
        }

    @app.patch("/v1/system/config")
    async def update_system_config(req: ConfigUpdateRequest, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "system.configure")
        actor = actor_payload.username
        return await rt.update_system_config(req.updates, actor=actor)

    @app.get("/v1/system/health/detailed")
    async def get_detailed_health(request: Request) -> Dict[str, Any]:
        require_permission(request, "health.view")
        return await rt.get_detailed_health()

    # ---------------------------------------------------------
    # Worker Console Unified Integration Endpoints
    # ---------------------------------------------------------

    @app.get("/v1/worker/{node_id}/overview")
    async def get_worker_overview(node_id: str, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "worker.view")
        if not rt.auth.check_node_access(actor_payload, node_id):
            raise HTTPException(status_code=403, detail="Forbidden: node scope mismatch")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        tasks = await rt.get_node_tasks(node_id, limit=200)
        active = [t for t in tasks if t.status == TaskStatus.RUNNING]
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in tasks if t.status == TaskStatus.FAILED]
        net = rt.network_estimator._metrics.get(node_id)

        return {
            "node_id": node_id,
            "hostname": n.capabilities.hostname or "localhost",
            "status": n.status.value,
            "connection_status": "connected" if n.status in (NodeStatus.ONLINE, NodeStatus.DEGRADED, NodeStatus.DRAINING) else "disconnected",
            "orchestrator_url": f"http://{rt.config.host}:{rt.config.port}",
            "uptime_seconds": int((utc_now() - n.first_seen).total_seconds()) if hasattr(n, "first_seen") else 0,
            "agent_version": "0.2.0",
            "cpu_percent": n.telemetry.cpu_percent if n.telemetry else 0.0,
            "ram_percent": n.telemetry.ram_percent if n.telemetry else 0.0,
            "gpu_percent": n.telemetry.gpu_percent if n.telemetry else None,
            "gpu_memory_used_mb": n.telemetry.gpu_memory_used_mb if n.telemetry else None,
            "has_gpu": n.capabilities.has_gpu,
            "gpu_name": n.capabilities.gpu_name,
            "gpu_vram_mb": n.capabilities.gpu_vram_mb,
            "active_tasks": len(active),
            "queued_tasks": 0,
            "completed_tasks": len(completed),
            "failed_tasks": len(failed),
            "worker_concurrency": n.capabilities.worker_capacity,
            "capacity_utilization": round((len(active) / n.capabilities.worker_capacity) * 100, 1) if n.capabilities.worker_capacity > 0 else 0,
            "rtt_ms": round(net.rtt_ms_ewma, 2) if net else 0.0,
            "upload_mbps": round(net.upload_mbps_ewma, 2) if net else 0.0,
            "download_mbps": round(net.download_mbps_ewma, 2) if net else 0.0,
            "is_local": n.capabilities.is_local,
            "base_score": n.base_score,
            "performance_multiplier": n.performance_multiplier,
            "effective_score": n.effective_score,
        }

    @app.get("/v1/worker/{node_id}/hardware")
    async def get_worker_hardware(node_id: str, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "worker.view")
        if not rt.auth.check_node_access(actor_payload, node_id):
            raise HTTPException(status_code=403, detail="Forbidden: node scope mismatch")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        caps = n.capabilities
        return {
            "node_id": node_id,
            "detected_hardware": {
                "cpu_cores": caps.cpu_cores,
                "cpu_frequency_mhz": caps.cpu_frequency_mhz,
                "ram_total_mb": caps.ram_total_mb,
                "ram_available_mb": caps.ram_available_mb,
                "has_gpu": caps.has_gpu,
                "gpu_name": caps.gpu_name,
                "gpu_vram_mb": caps.gpu_vram_mb,
                "os": caps.os,
                "arch": caps.arch,
            },
            "scheduler_registered": {
                "supported_handlers": caps.supported_handlers,
                "tags": caps.tags,
                "is_local": caps.is_local,
                "worker_capacity": caps.worker_capacity,
                "base_score": n.base_score,
                "performance_multiplier": n.performance_multiplier,
                "effective_score": n.effective_score,
            },
        }

    @app.get("/v1/worker/{node_id}/tasks")
    async def get_worker_tasks(node_id: str, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "worker.view")
        if not rt.auth.check_node_access(actor_payload, node_id):
            raise HTTPException(status_code=403, detail="Forbidden: node scope mismatch")
        tasks = await rt.get_node_tasks(node_id, limit=200)
        active = [t.model_dump(mode="json") for t in tasks if t.status == TaskStatus.RUNNING]
        completed = [t.model_dump(mode="json") for t in tasks if t.status == TaskStatus.COMPLETED]
        failed = [t.model_dump(mode="json") for t in tasks if t.status == TaskStatus.FAILED]
        return {
            "node_id": node_id,
            "active_tasks": active,
            "recent_completed": completed[:25],
            "recent_failed": failed[:25],
            "total_tasks": len(tasks),
        }

    @app.get("/v1/worker/{node_id}/pool")
    async def get_worker_pool(node_id: str, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "worker.view")
        if not rt.auth.check_node_access(actor_payload, node_id):
            raise HTTPException(status_code=403, detail="Forbidden: node scope mismatch")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        tasks = await rt.repo.find_by_assigned_node(node_id, status=TaskStatus.RUNNING)
        active = len(tasks)
        capacity = n.capabilities.worker_capacity
        return {
            "node_id": node_id,
            "concurrency": capacity,
            "active_slots": active,
            "available_slots": max(0, capacity - active),
            "utilization_percent": round((active / capacity) * 100, 1) if capacity > 0 else 0,
            "supported_handlers": n.capabilities.supported_handlers,
        }

    @app.get("/v1/worker/{node_id}/network")
    async def get_worker_network(node_id: str, request: Request) -> Dict[str, Any]:
        actor_payload = require_permission(request, "worker.view")
        if not rt.auth.check_node_access(actor_payload, node_id):
            raise HTTPException(status_code=403, detail="Forbidden: node scope mismatch")
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        net = rt.network_estimator._metrics.get(node_id)
        return {
            "node_id": node_id,
            "websocket_status": "connected" if n.status != NodeStatus.OFFLINE else "disconnected",
            "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            "rtt_ms_ewma": round(net.rtt_ms_ewma, 2) if net else 0.0,
            "upload_mbps_ewma": round(net.upload_mbps_ewma, 2) if net else 0.0,
            "download_mbps_ewma": round(net.download_mbps_ewma, 2) if net else 0.0,
            "transfers_count": net.transfers_count if net else 0,
            "transfer_failures": net.transfer_failures if net else 0,
            "chunk_size_bytes": rt.config.chunk_size_bytes,
        }

    # ---------------------------------------------------------
    # REST API Routes: DLQ
    # ---------------------------------------------------------

    @app.get("/v1/dlq")
    async def list_dlq(request: Request) -> List[Any]:
        require_permission(request, "dlq.view")
        items = await rt.dlq.list_items()
        return [i.model_dump(mode="json") for i in items]

    @app.post("/v1/dlq/{task_id}/recover", response_model=Task)
    async def recover_dlq(task_id: str, request: Request) -> Task:
        require_permission(request, "dlq.manage")
        recovered = await rt.dlq.recover(task_id)
        if not recovered:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not in DLQ")
        await rt.repo.save(recovered)
        await rt.queue.enqueue(recovered)
        return recovered

    # ---------------------------------------------------------
    # REST API Routes: Primary / Standby Replication & Failover
    # ---------------------------------------------------------

    @app.get("/v1/standby/snapshot")
    async def get_standby_snapshot(request: Request) -> Dict[str, Any]:
        require_permission(request, "recovery.view")
        return await rt.create_snapshot()

    @app.get("/v1/standby/status")
    async def get_standby_status(request: Request) -> Dict[str, Any]:
        require_permission(request, "recovery.view")
        return {
            "standby_mode": rt.config.standby_mode,
            "primary_url": rt.config.primary_url,
            "snapshot_interval_seconds": rt.config.snapshot_interval_seconds,
        }

    @app.post("/v1/standby/promote")
    async def promote_standby(request: Request) -> Dict[str, str]:
        require_permission(request, "recovery.manage")
        await rt.promote_to_primary()
        return {"status": "promoted", "role": "primary"}

    # ---------------------------------------------------------
    # WebSocket Endpoint: Compute Nodes
    # ---------------------------------------------------------

    @app.websocket("/v1/ws/nodes")
    async def websocket_node_endpoint(websocket: WebSocket):
        await websocket.accept()
        node_id = None
        try:
            # 1. First message must be REGISTER_NODE
            raw_reg = await websocket.receive_text()
            reg_msg = ProtocolMessage.model_validate(json.loads(raw_reg))

            if reg_msg.message_type != MessageType.REGISTER_NODE:
                await websocket.close(code=1008, reason="Expected REGISTER_NODE")
                return

            # Validate security signature and replay protection in secure mode
            is_valid, sec_err = rt.security.validate_incoming(reg_msg)
            if not is_valid:
                logger.warning(f"Registration rejected due to security check: {sec_err}")
                ack = ProtocolMessage(
                    message_type=MessageType.REGISTER_ACK,
                    payload=RegisterAckPayload(node_id=reg_msg.node_id or "unknown", accepted=False, message=f"Security rejection: {sec_err}").model_dump(mode="json"),
                )
                await websocket.send_text(json.dumps(ack.model_dump(mode="json")))
                await websocket.close(code=1008, reason=f"Security rejection: {sec_err}")
                return

            reg_payload = RegisterNodePayload.model_validate(reg_msg.payload)

            # Authenticate join token
            if reg_payload.token != rt.config.join_token:
                logger.warning(f"Node [{reg_payload.node_id}] failed authentication join token")
                ack = ProtocolMessage(
                    message_type=MessageType.REGISTER_ACK,
                    payload=RegisterAckPayload(node_id=reg_payload.node_id, accepted=False, message="Invalid token").model_dump(mode="json"),
                )
                await websocket.send_text(json.dumps(ack.model_dump(mode="json")))
                await websocket.close(code=1008, reason="Invalid join token")
                return

            node_id = reg_payload.node_id
            profile = NodeProfile(
                id=node_id,
                status=NodeStatus.ONLINE,
                capabilities=reg_payload.capabilities,
            )

            # Register node
            await rt.registry.register(profile, websocket)

            # Send RegisterAck
            ack = ProtocolMessage(
                message_type=MessageType.REGISTER_ACK,
                payload=RegisterAckPayload(
                    node_id=node_id,
                    accepted=True,
                    message="Registered successfully",
                    heartbeat_interval_seconds=rt.config.heartbeat_interval_seconds,
                    telemetry_interval_seconds=5.0,
                ).model_dump(mode="json"),
            )
            await websocket.send_text(json.dumps(ack.model_dump(mode="json")))
            logger.info(f"Node [{node_id}] successfully connected and registered")
            await rt.events.broadcast(
                event_type="node.registered",
                data={
                    "node_id": node_id,
                    "status": NodeStatus.ONLINE.value,
                    "capabilities": reg_payload.capabilities.model_dump(mode="json"),
                },
                entity_id=node_id,
            )

            # 2. Main message loop
            while True:
                msg_text = await websocket.receive_text()
                await rt.handle_node_message(websocket, msg_text)

        except WebSocketDisconnect:
            if node_id:
                logger.warning(f"Node [{node_id}] disconnected")
                await rt.registry.mark_offline(node_id)
                await rt._recover_tasks_for_failed_node(node_id)
                await rt.events.broadcast(
                    event_type="node.disconnected",
                    data={"node_id": node_id, "status": NodeStatus.OFFLINE.value},
                    entity_id=node_id,
                )
        except Exception as e:
            logger.error(f"WebSocket error for node [{node_id}]: {e}", exc_info=True)
            if node_id:
                await rt.registry.mark_offline(node_id)
                await rt._recover_tasks_for_failed_node(node_id)
                await rt.events.broadcast(
                    event_type="node.disconnected",
                    data={"node_id": node_id, "status": NodeStatus.OFFLINE.value, "error": str(e)},
                    entity_id=node_id,
                )

    # ---------------------------------------------------------
    # WebSocket Endpoint: Real-Time Dashboard Events Hub
    # ---------------------------------------------------------

    @app.websocket("/v1/ws/dashboard")
    async def websocket_dashboard_endpoint(websocket: WebSocket):
        token = websocket.query_params.get("token")
        if not token:
            auth_hdr = websocket.headers.get("authorization", "")
            if auth_hdr.startswith("Bearer "):
                token = auth_hdr[7:].strip()
            elif "sec-websocket-protocol" in websocket.headers:
                protocols = [p.strip() for p in websocket.headers["sec-websocket-protocol"].split(",")]
                for p in protocols:
                    if p.startswith("bearer-"):
                        token = p[7:].strip()

        payload = None
        if token:
            if token == rt.config.join_token:
                payload = TokenPayload(
                    username="cluster-service",
                    role=UserRole.SUPER_ADMIN,
                    node_scope=None,
                    permissions=sorted(list(PERMISSIONS_MAP[UserRole.SUPER_ADMIN])),
                    exp=time.time() + 86400,
                )
            else:
                payload = rt.auth.validate_token(token)

        if not payload or not rt.auth.check_permission(payload, "cluster.view"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
            return

        await websocket.accept()
        await rt.events.register(websocket)
        try:
            # Send initial sync payload
            health = await get_cluster_health()
            await websocket.send_text(json.dumps({
                "event_type": "initial_sync",
                "timestamp": utc_now().isoformat(),
                "data": health.model_dump(mode="json"),
            }))
            while True:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await rt.events.unregister(websocket)
        except Exception:
            await rt.events.unregister(websocket)

    # ---------------------------------------------------------
    # Frontend Dashboard UI
    # ---------------------------------------------------------
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_dashboard() -> FileResponse:
            index_file = static_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Dashboard UI not found")

    return app
