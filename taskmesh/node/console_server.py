"""Embedded Worker Agent Console HTTP & WebSocket API Server."""

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from taskmesh.core.enums import NodeStatus, TaskStatus
from taskmesh.core.models import utc_now

logger = logging.getLogger("taskmesh.node.console")


class ConcurrencyUpdateRequest(BaseModel):
    concurrency: int


class MaintenanceRequest(BaseModel):
    maintenance: bool


def create_worker_console_app(agent: Any) -> FastAPI:
    """Creates a FastAPI app for the local Worker Agent Console."""
    app = FastAPI(
        title=f"TaskMesh Worker Console - {agent.node_id}",
        version="0.2.0",
        description="Local Node Agent Management and Hardware Monitoring Interface",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    start_time = time.time()

    # -------------------------------------------------------------
    # Worker Console REST Endpoints
    # -------------------------------------------------------------

    @app.get("/api/worker/overview")
    async def get_overview() -> Dict[str, Any]:
        uptime_sec = int(time.time() - start_time)
        active_count = agent.pool.active_count
        concurrency = agent.config.worker_concurrency

        from taskmesh.node.hardware import collect_telemetry
        telem = collect_telemetry(
            node_id=agent.node_id,
            active_tasks=active_count,
            queued_tasks=0,
            rtt_ms_ewma=agent.rtt_ms_ewma,
            upload_mbps_ewma=agent.upload_mbps_ewma,
            download_mbps_ewma=agent.download_mbps_ewma,
        )

        completed_count = getattr(agent, "_tasks_completed_count", 0)
        failed_count = getattr(agent, "_tasks_failed_count", 0)

        # Connection status check safely supporting various websockets library versions
        is_connected = False
        if agent._ws is not None:
            state = getattr(agent._ws, "state", None)
            if state is not None:
                # In websockets 14+, State.OPEN == 1 or "OPEN"
                is_connected = str(state).upper() in ["1", "OPEN", "STATE.OPEN"]
            elif hasattr(agent._ws, "closed"):
                is_connected = not agent._ws.closed
            else:
                is_connected = True
        ws_status = "connected" if is_connected else "disconnected"

        status_val = agent.status.value
        if getattr(agent, "_maintenance_mode", False):
            status_val = "maintenance"

        return {
            "node_id": agent.node_id,
            "hostname": agent.capabilities.hostname or "localhost",
            "status": status_val,
            "connection_status": ws_status,
            "orchestrator_url": agent.config.orchestrator_url,
            "uptime_seconds": uptime_sec,
            "agent_version": "0.2.0",
            "cpu_percent": telem.cpu_percent,
            "ram_percent": telem.ram_percent,
            "gpu_percent": telem.gpu_percent,
            "gpu_memory_used_mb": telem.gpu_memory_used_mb,
            "has_gpu": agent.capabilities.has_gpu,
            "gpu_name": agent.capabilities.gpu_name,
            "gpu_vram_mb": agent.capabilities.gpu_vram_mb,
            "active_tasks": active_count,
            "queued_tasks": 0,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "worker_concurrency": concurrency,
            "capacity_utilization": round((active_count / concurrency) * 100, 1) if concurrency > 0 else 0,
            "rtt_ms": round(agent.rtt_ms_ewma, 2),
            "upload_mbps": round(agent.upload_mbps_ewma, 2),
            "download_mbps": round(agent.download_mbps_ewma, 2),
            "is_local": agent.config.is_local,
            "paused_assignments": getattr(agent, "_paused_assignments", False),
        }

    @app.get("/api/worker/hardware")
    async def get_hardware() -> Dict[str, Any]:
        caps = agent.capabilities
        return {
            "node_id": agent.node_id,
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
                "supported_handlers": agent.pool.get_supported_handlers(),
                "tags": caps.tags,
                "is_local": caps.is_local,
                "worker_capacity": agent.config.worker_concurrency,
            },
        }

    @app.get("/api/worker/tasks")
    async def get_tasks() -> Dict[str, Any]:
        history = list(getattr(agent, "_task_history", deque()))
        active = [t for t in history if t.get("status") == "running"]
        completed = [t for t in history if t.get("status") == "completed"]
        failed = [t for t in history if t.get("status") == "failed"]

        return {
            "node_id": agent.node_id,
            "active_tasks": active,
            "recent_completed": completed[-25:],
            "recent_failed": failed[-25:],
            "total_recorded": len(history),
        }

    @app.get("/api/worker/pool")
    async def get_pool() -> Dict[str, Any]:
        active = agent.pool.active_count
        concurrency = agent.config.worker_concurrency
        available = max(0, concurrency - active)

        return {
            "node_id": agent.node_id,
            "concurrency": concurrency,
            "active_slots": active,
            "available_slots": available,
            "utilization_percent": round((active / concurrency) * 100, 1) if concurrency > 0 else 0,
            "supported_handlers": agent.pool.get_supported_handlers(),
            "paused_assignments": getattr(agent, "_paused_assignments", False),
        }

    @app.get("/api/worker/network")
    async def get_network() -> Dict[str, Any]:
        is_connected = False
        if agent._ws is not None:
            state = getattr(agent._ws, "state", None)
            if state is not None:
                is_connected = str(state).upper() in ["1", "OPEN", "STATE.OPEN"]
            elif hasattr(agent._ws, "closed"):
                is_connected = not agent._ws.closed
            else:
                is_connected = True
        ws_status = "connected" if is_connected else "disconnected"
        return {
            "node_id": agent.node_id,
            "orchestrator_url": agent.config.orchestrator_url,
            "standby_url": agent.config.standby_url,
            "websocket_status": ws_status,
            "sequence_number": agent._seq_num,
            "rtt_ms_ewma": round(agent.rtt_ms_ewma, 2),
            "upload_mbps_ewma": round(agent.upload_mbps_ewma, 2),
            "download_mbps_ewma": round(agent.download_mbps_ewma, 2),
            "chunk_size_bytes": agent.config.chunk_size_bytes,
            "max_payload_size_bytes": agent.config.max_payload_size_bytes,
            "protocol": {
                "control_messages": "JSON text frames over WSS",
                "binary_payloads": "48-byte TMCH header chunks (64KB default) + SHA-256 verification",
            },
        }

    @app.get("/api/worker/logs")
    async def get_logs(limit: int = 100, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = list(getattr(agent, "_logs_buffer", deque()))
        if severity:
            logs = [l for l in logs if l.get("severity") == severity.upper()]
        return logs[:limit]

    # -------------------------------------------------------------
    # Worker Operations
    # -------------------------------------------------------------

    @app.post("/api/worker/drain")
    async def drain_node() -> Dict[str, str]:
        agent.status = NodeStatus.DRAINING
        logger.info(f"Worker [{agent.node_id}] instructed to DRAIN from Console")
        return {"status": "draining", "node_id": agent.node_id}

    @app.post("/api/worker/resume")
    async def resume_node() -> Dict[str, str]:
        agent.status = NodeStatus.ONLINE
        setattr(agent, "_maintenance_mode", False)
        setattr(agent, "_paused_assignments", False)
        logger.info(f"Worker [{agent.node_id}] instructed to RESUME from Console")
        return {"status": "online", "node_id": agent.node_id}

    @app.post("/api/worker/maintenance")
    async def maintenance_node(req: MaintenanceRequest) -> Dict[str, Any]:
        setattr(agent, "_maintenance_mode", req.maintenance)
        agent.status = NodeStatus.MAINTENANCE if req.maintenance else NodeStatus.ONLINE
        logger.info(f"Worker [{agent.node_id}] maintenance set to {req.maintenance}")
        return {"maintenance": req.maintenance, "status": agent.status.value, "node_id": agent.node_id}

    @app.post("/api/worker/concurrency")
    async def update_concurrency(req: ConcurrencyUpdateRequest) -> Dict[str, Any]:
        if req.concurrency < 1 or req.concurrency > 64:
            raise HTTPException(status_code=400, detail="Concurrency must be between 1 and 64")
        agent.config.worker_concurrency = req.concurrency
        # Update pool semaphore
        agent.pool._semaphore = asyncio.Semaphore(req.concurrency)
        logger.info(f"Worker [{agent.node_id}] concurrency updated to {req.concurrency}")
        return {"concurrency": req.concurrency, "node_id": agent.node_id}

    @app.post("/api/worker/pause_assignments")
    async def toggle_pause() -> Dict[str, Any]:
        cur = getattr(agent, "_paused_assignments", False)
        new_val = not cur
        setattr(agent, "_paused_assignments", new_val)
        logger.info(f"Worker [{agent.node_id}] pause_assignments toggled to {new_val}")
        return {"paused_assignments": new_val, "node_id": agent.node_id}

    @app.get("/api/worker/identity")
    async def get_identity() -> Dict[str, Any]:
        status_val = agent.status.value
        if getattr(agent, "_maintenance_mode", False):
            status_val = "maintenance"
        return {
            "node_id": agent.node_id,
            "hostname": agent.capabilities.hostname or "localhost",
            "orchestrator_url": agent.config.orchestrator_url,
            "status": status_val,
            "is_worker": True,
            "agent_version": "0.2.0",
        }

    # -------------------------------------------------------------
    # Static UI Serving (Dedicated Worker Agent Console UI)
    # -------------------------------------------------------------
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if not os.path.exists(static_dir):
        # Fallback to orchestrator static only if worker static is not yet built
        fallback = os.path.join(os.path.dirname(__file__), "..", "orchestrator", "static")
        if os.path.exists(fallback):
            static_dir = fallback

    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_worker_console() -> FileResponse:
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="Worker Console UI not found")

    return app


async def start_console_server(agent: Any, port: int) -> None:
    """Launches the worker console server in the background."""
    app = create_worker_console_app(agent)
    cfg = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    logger.info(f"Worker Agent Console active at http://0.0.0.0:{port} (Node: {agent.node_id})")
    await server.serve()
