"""FastAPI server and routes for the TaskMesh Orchestrator."""

from contextlib import asynccontextmanager
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import MessageType, NodeStatus, OffloadPolicy, SchedulerMode, TaskStatus

from taskmesh.core.errors import TaskNotFoundError
from taskmesh.core.models import NodeProfile, Task, TaskCreate
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import SQLiteTaskRepository
from taskmesh.protocol.messages import (
    ProtocolMessage,
    RegisterAckPayload,
    RegisterNodePayload,
)

logger = logging.getLogger("taskmesh.server")


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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.runtime = rt

    # ---------------------------------------------------------
    # REST API Routes: Tasks
    # ---------------------------------------------------------

    @app.post("/v1/tasks", response_model=Task, status_code=201)
    async def submit_task(req: TaskCreate) -> Task:
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
    async def get_task_payload(task_id: str) -> Response:
        payload_data = await rt.payload_store.get_payload(task_id)
        if not payload_data:
            raise HTTPException(status_code=404, detail=f"No binary payload found for task {task_id}")
        meta = await rt.payload_store.get_meta(task_id)
        media_type = meta.mime_type if meta else "application/octet-stream"
        return Response(content=payload_data, media_type=media_type)

    @app.get("/v1/tasks", response_model=List[Task])
    async def list_tasks(
        status: Optional[TaskStatus] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ) -> List[Task]:
        return await rt.repo.list(status=status, limit=limit)

    @app.get("/v1/tasks/{task_id}", response_model=Task)
    async def get_task(task_id: str) -> Task:
        t = await rt.repo.get(task_id)
        if not t:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return t

    @app.post("/v1/tasks/{task_id}/cancel", response_model=Task)
    async def cancel_task(task_id: str, reason: str = "Client cancellation") -> Task:
        try:
            return await rt.cancel_task(task_id, reason=reason)
        except TaskNotFoundError:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    @app.post("/v1/tasks/{task_id}/retry", response_model=Task)
    async def retry_task(task_id: str) -> Task:
        try:
            return await rt.retry_task(task_id)
        except TaskNotFoundError:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # ---------------------------------------------------------
    # REST API Routes: Nodes & Cluster
    # ---------------------------------------------------------

    @app.get("/v1/nodes", response_model=List[NodeProfile])
    async def list_nodes(status: Optional[NodeStatus] = Query(None)) -> List[NodeProfile]:
        return await rt.registry.list_nodes(status=status)

    @app.get("/v1/nodes/{node_id}", response_model=NodeProfile)
    async def get_node(node_id: str) -> NodeProfile:
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return n

    @app.post("/v1/nodes/{node_id}/drain")
    async def drain_node(node_id: str) -> Dict[str, str]:
        n = await rt.registry.get_node(node_id)
        if not n:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        await rt.drain_node(node_id)
        return {"status": "draining", "node_id": node_id}

    @app.get("/v1/cluster/health", response_model=ClusterHealthResponse)
    async def cluster_health() -> ClusterHealthResponse:
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

    # ---------------------------------------------------------
    # REST API Routes: Scheduler & Explainability
    # ---------------------------------------------------------

    @app.get("/v1/scheduler/status")
    async def scheduler_status() -> Dict[str, Any]:
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
    async def scheduler_decisions(limit: int = Query(50, ge=1, le=200)) -> List[Any]:
        return await rt.get_decisions(limit=limit)


    # ---------------------------------------------------------
    # REST API Routes: DLQ
    # ---------------------------------------------------------

    @app.get("/v1/dlq")
    async def list_dlq() -> List[Any]:
        items = await rt.dlq.list_items()
        return [i.model_dump(mode="json") for i in items]

    @app.post("/v1/dlq/{task_id}/recover", response_model=Task)
    async def recover_dlq(task_id: str) -> Task:
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
    async def get_standby_snapshot() -> Dict[str, Any]:
        return await rt.create_snapshot()

    @app.get("/v1/standby/status")
    async def get_standby_status() -> Dict[str, Any]:
        return {
            "standby_mode": rt.config.standby_mode,
            "primary_url": rt.config.primary_url,
            "snapshot_interval_seconds": rt.config.snapshot_interval_seconds,
        }

    @app.post("/v1/standby/promote")
    async def promote_standby() -> Dict[str, str]:
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

            # 2. Main message loop
            while True:
                msg_text = await websocket.receive_text()
                await rt.handle_node_message(websocket, msg_text)

        except WebSocketDisconnect:
            if node_id:
                logger.warning(f"Node [{node_id}] disconnected")
                await rt.registry.mark_offline(node_id)
                await rt._recover_tasks_for_failed_node(node_id)
        except Exception as e:
            logger.error(f"WebSocket error for node [{node_id}]: {e}", exc_info=True)
            if node_id:
                await rt.registry.mark_offline(node_id)
                await rt._recover_tasks_for_failed_node(node_id)

    return app
