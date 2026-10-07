"""Domain exceptions for TaskMesh."""


class TaskMeshError(Exception):
    """Base exception for all TaskMesh errors."""
    pass


class TaskNotFoundError(TaskMeshError):
    """Raised when a task does not exist."""
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id


class NodeNotFoundError(TaskMeshError):
    """Raised when a node does not exist."""
    def __init__(self, node_id: str):
        super().__init__(f"Node not found: {node_id}")
        self.node_id = node_id


class IneligibleNodeError(TaskMeshError):
    """Raised when no nodes meet task requirements."""
    pass


class DuplicateTaskError(TaskMeshError):
    """Raised when an idempotency key collides."""
    def __init__(self, key: str, task_id: str):
        super().__init__(f"Duplicate submission with idempotency key '{key}' matches task: {task_id}")
        self.key = key
        self.task_id = task_id


class LeaseExpiredError(TaskMeshError):
    """Raised when an operation is attempted with an expired lease."""
    pass


class InvalidStateTransitionError(TaskMeshError):
    """Raised when an invalid task or node state transition is requested."""
    pass


class AuthenticationError(TaskMeshError):
    """Raised when node or client authentication fails."""
    pass


class ProtocolVersionError(TaskMeshError):
    """Raised when incompatible protocol versions are used."""
    pass
