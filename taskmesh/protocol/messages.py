"""Typed WebSocket protocol messages and schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from taskmesh.core.enums import MessageType, NodeStatus, TaskStatus
from taskmesh.core.models import CheckpointData, NodeCapabilities, NodeTelemetry, TaskResult
from taskmesh.protocol.version import PROTOCOL_VERSION


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BasePayload(BaseModel):
    """Base class for protocol message payloads."""
    pass


class RegisterNodePayload(BasePayload):
    node_id: str
    token: str
    capabilities: NodeCapabilities


class RegisterAckPayload(BasePayload):
    node_id: str
    accepted: bool
    message: str = "Registered successfully"
    heartbeat_interval_seconds: float = 3.0
    telemetry_interval_seconds: float = 5.0


class HeartbeatPayload(BasePayload):
    node_id: str
    sequence_number: int
    status: NodeStatus = NodeStatus.ONLINE
    active_tasks: int = 0


class TelemetryPayload(BasePayload):
    node_id: str
    telemetry: NodeTelemetry


class TaskOfferPayload(BasePayload):
    task_id: str
    task_type: str
    priority: int
    requires_gpu: bool
    required_memory_mb: int
    deadline_seconds: float = 60.0


class TaskBidPayload(BasePayload):
    task_id: str
    node_id: str
    bid_value: float
    estimated_duration_seconds: float
    can_execute: bool
    reasons: Optional[str] = None


class TaskAssignmentPayload(BasePayload):
    task_id: str
    attempt_id: str
    lease_id: str
    lease_expires_at: datetime
    task_type: str
    payload: Dict[str, Any]
    priority: int
    timeout_seconds: float
    checkpoint_state: Optional[Dict[str, Any]] = None


class TaskAcceptedPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str


class TaskRejectedPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    reason: str


class TaskStartedPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    started_at: datetime = Field(default_factory=utc_now)


class TaskProgressPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    progress: float = Field(..., ge=0.0, le=1.0)
    message: Optional[str] = None


class TaskCheckpointPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    checkpoint: CheckpointData


class TaskCompletedPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    result: TaskResult


class TaskFailedPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str
    error: str
    execution_time_seconds: float = 0.0


class TaskCancelPayload(BasePayload):
    task_id: str
    attempt_id: Optional[str] = None
    reason: str = "Cancelled by client"


class TaskCancelledPayload(BasePayload):
    task_id: str
    attempt_id: str
    node_id: str


class NodeDrainPayload(BasePayload):
    node_id: str
    grace_period_seconds: float = 30.0


class ErrorPayload(BasePayload):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ProtocolMessage(BaseModel):
    """Universal typed envelope for TaskMesh WebSocket protocol messages."""
    protocol_version: str = PROTOCOL_VERSION
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType
    node_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    sequence_number: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
