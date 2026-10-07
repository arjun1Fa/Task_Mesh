"""Configuration management for TaskMesh."""

import os
from typing import Optional
from pydantic import BaseModel, Field

from taskmesh.core.enums import SchedulerMode


class OrchestratorConfig(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("TASKMESH_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("TASKMESH_PORT", "8000")))
    join_token: str = Field(default_factory=lambda: os.getenv("TASKMESH_JOIN_TOKEN", "default-mesh-secret"))
    data_dir: str = Field(default_factory=lambda: os.getenv("TASKMESH_DATA_DIR", "./data"))
    db_url: str = Field(default_factory=lambda: os.getenv("TASKMESH_DB_URL", "sqlite:///./taskmesh.db"))

    # Timing & Leases
    heartbeat_interval_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_HEARTBEAT_INTERVAL", "3.0")))
    node_timeout_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_NODE_TIMEOUT", "9.0")))
    task_lease_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_LEASE_SECONDS", "30.0")))
    scheduler_poll_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_SCHEDULER_POLL", "0.5")))

    # Scheduling Policies
    scheduler_mode: SchedulerMode = Field(
        default_factory=lambda: SchedulerMode(os.getenv("TASKMESH_SCHEDULER_MODE", "adaptive"))
    )
    ewma_alpha: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_EWMA_ALPHA", "0.2")))
    mwu_eta: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_MWU_ETA", "0.1")))
    rl_learning_rate: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_RL_LR", "0.1")))
    rl_discount_factor: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_RL_GAMMA", "0.9")))
    rl_epsilon: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_RL_EPSILON", "0.15")))

    # Standby replication
    standby_mode: bool = Field(default_factory=lambda: os.getenv("TASKMESH_STANDBY_MODE", "false").lower() == "true")
    primary_url: Optional[str] = Field(default_factory=lambda: os.getenv("TASKMESH_PRIMARY_URL", None))
    snapshot_interval_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_SNAPSHOT_INTERVAL", "5.0")))


class NodeConfig(BaseModel):
    node_id: str = Field(default_factory=lambda: os.getenv("TASKMESH_NODE_ID", f"node-{os.getpid()}"))
    orchestrator_url: str = Field(default_factory=lambda: os.getenv("TASKMESH_ORCHESTRATOR_URL", "ws://127.0.0.1:8000/v1/ws/nodes"))
    join_token: str = Field(default_factory=lambda: os.getenv("TASKMESH_JOIN_TOKEN", "default-mesh-secret"))
    worker_concurrency: int = Field(default_factory=lambda: int(os.getenv("TASKMESH_WORKERS", "4")))
    heartbeat_interval_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_HEARTBEAT_INTERVAL", "3.0")))
    telemetry_interval_seconds: float = Field(default_factory=lambda: float(os.getenv("TASKMESH_TELEMETRY_INTERVAL", "5.0")))
    tags: str = Field(default_factory=lambda: os.getenv("TASKMESH_TAGS", "cpu,general"))
