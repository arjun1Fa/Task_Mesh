"""Core enumerations for TaskMesh."""

from enum import Enum


class TaskStatus(str, Enum):
    """Lifecycle states of a task in TaskMesh."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    DLQ = "dlq"

    def is_terminal(self) -> bool:
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.DLQ,
        )


class NodeStatus(str, Enum):
    """Lifecycle states of a compute node."""
    ONLINE = "online"
    DEGRADED = "degraded"
    DRAINING = "draining"
    OFFLINE = "offline"


class SchedulerMode(str, Enum):
    """Supported task scheduler policies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    HIGHEST_BID = "highest_bid"
    ADAPTIVE = "adaptive"


class MessageType(str, Enum):
    """Typed WebSocket protocol message types."""
    REGISTER_NODE = "register_node"
    REGISTER_ACK = "register_ack"
    HEARTBEAT = "heartbeat"
    TELEMETRY = "telemetry"
    TASK_OFFER = "task_offer"
    TASK_BID = "task_bid"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_ACCEPTED = "task_accepted"
    TASK_REJECTED = "task_rejected"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_CHECKPOINT = "task_checkpoint"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCEL = "task_cancel"
    TASK_CANCELLED = "task_cancelled"
    NODE_DRAIN = "node_drain"
    ERROR = "error"
