"""Domain models for TaskMesh using Pydantic v2."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, field_validator

from taskmesh.core.enums import NodeStatus, TaskStatus, OffloadPolicy


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BinaryPayloadMeta(BaseModel):
    """Metadata envelope for binary payload transport (e.g. images, tensors)."""
    payload_id: str = Field(default_factory=lambda: f"payload_{uuid.uuid4().hex[:12]}")
    task_id: str
    attempt_id: Optional[str] = None
    workload_type: str = "image_inference"
    model_identifier: str = "yolov8n"
    payload_size_bytes: int = 0
    mime_type: str = "image/jpeg"
    checksum_sha256: str = ""
    compression: str = "none"
    chunk_size_bytes: int = 65536
    total_chunks: int = 1

    # Future streaming extensions
    stream_id: Optional[str] = None
    frame_id: Optional[int] = None
    sequence_number: Optional[int] = None
    is_last_frame: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1)
    base_delay_seconds: float = Field(default=1.0, ge=0.0)
    max_delay_seconds: float = Field(default=60.0, ge=0.0)
    jitter: bool = Field(default=True)


class TaskLease(BaseModel):
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    attempt_id: str
    node_id: str
    granted_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        reference = now or utc_now()
        return reference > self.expires_at


class CheckpointData(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    attempt_id: str
    step: int = 0
    state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class TaskResult(BaseModel):
    task_id: str
    attempt_id: str
    node_id: str
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=utc_now)


class TaskCreate(BaseModel):
    task_type: str = Field(..., description="Handler or job type, e.g. 'log', 'cpu_test', 'image_inference'")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, description="Higher integer executes earlier")
    idempotency_key: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    repeat_every_seconds: Optional[float] = None
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    requires_gpu: bool = False
    required_memory_mb: int = 0
    required_capabilities: List[str] = Field(default_factory=list)
    preferred_capabilities: List[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    supports_checkpoint: bool = False
    offload_policy: OffloadPolicy = Field(default=OffloadPolicy.WIRELESS_ALLOWED)
    binary_meta: Optional[BinaryPayloadMeta] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    idempotency_key: Optional[str] = None
    task_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    scheduled_at: Optional[datetime] = None
    repeat_every_seconds: Optional[float] = None
    timeout_seconds: float = 60.0

    # Distributed Execution State
    assigned_node_id: Optional[str] = None
    current_attempt: int = 0
    current_attempt_id: Optional[str] = None
    active_lease: Optional[TaskLease] = None

    # Capabilities & Requirements
    requires_gpu: bool = False
    required_memory_mb: int = 0
    required_capabilities: List[str] = Field(default_factory=list)
    preferred_capabilities: List[str] = Field(default_factory=list)
    supports_checkpoint: bool = False

    # Wireless & Offloading Policy
    offload_policy: OffloadPolicy = Field(default=OffloadPolicy.WIRELESS_ALLOWED)
    binary_meta: Optional[BinaryPayloadMeta] = None

    # Retry & Fault Handling
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    retry_count: int = 0
    error_message: Optional[str] = None

    # Progress & Results
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    latest_checkpoint: Optional[CheckpointData] = None
    result: Optional[TaskResult] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def next_attempt(self, node_id: str, lease_duration_seconds: float) -> str:
        self.current_attempt += 1
        self.current_attempt_id = f"{self.id}-A{self.current_attempt}"
        self.assigned_node_id = node_id
        now = utc_now()
        expires = datetime.fromtimestamp(now.timestamp() + lease_duration_seconds, timezone.utc)
        self.active_lease = TaskLease(
            task_id=self.id,
            attempt_id=self.current_attempt_id,
            node_id=node_id,
            granted_at=now,
            expires_at=expires,
        )
        self.status = TaskStatus.RUNNING
        self.updated_at = now
        return self.current_attempt_id


class NodeCapabilities(BaseModel):
    cpu_cores: int = 1
    cpu_frequency_mhz: float = 2000.0
    ram_total_mb: int = 1024
    ram_available_mb: int = 1024
    has_gpu: bool = False
    gpu_name: Optional[str] = None
    gpu_vram_mb: int = 0
    os: str = "unknown"
    arch: str = "x86_64"
    supported_handlers: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    worker_capacity: int = 4
    # Wireless & Networking identification
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    port: Optional[int] = None
    is_local: bool = False
    models_loaded: List[str] = Field(default_factory=list)


class NodeTelemetry(BaseModel):
    node_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: Optional[float] = None
    gpu_memory_used_mb: Optional[int] = None
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks_total: int = 0
    failed_tasks_total: int = 0
    network_latency_ms: float = 0.0
    # Wireless Telemetry
    rtt_ms_ewma: float = 0.0
    upload_mbps_ewma: float = 0.0
    download_mbps_ewma: float = 0.0
    transfer_failures: int = 0
    last_transfer_time_ms: float = 0.0



class NodeProfile(BaseModel):
    id: str
    status: NodeStatus = NodeStatus.ONLINE
    capabilities: NodeCapabilities = Field(default_factory=NodeCapabilities)
    telemetry: Optional[NodeTelemetry] = None
    first_seen: datetime = Field(default_factory=utc_now)
    last_heartbeat: datetime = Field(default_factory=utc_now)
    last_telemetry: Optional[datetime] = None
    base_score: float = 1.0
    performance_multiplier: float = 1.0
    drr_deficit: float = 0.0
    total_assigned: int = 0
    total_completed: int = 0
    total_failed: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def effective_score(self) -> float:
        return max(0.01, self.base_score * self.performance_multiplier)
