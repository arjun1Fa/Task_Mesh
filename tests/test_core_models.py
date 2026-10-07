"""Unit tests for TaskMesh core models and lifecycle."""

from datetime import datetime, timezone
import pytest
from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import RetryPolicy, Task, TaskCreate, TaskLease, utc_now


def test_task_creation_and_defaults():
    req = TaskCreate(
        task_type="cpu_test",
        payload={"iterations": 100},
        priority=10,
        requires_gpu=False,
    )
    task = Task(
        task_type=req.task_type,
        payload=req.payload,
        priority=req.priority,
    )
    assert task.status == TaskStatus.PENDING
    assert task.current_attempt == 0
    assert task.assigned_node_id is None
    assert task.priority == 10


def test_task_attempt_and_lease():
    task = Task(task_type="log", payload={"msg": "hi"})
    attempt_id = task.next_attempt("node-test-1", lease_duration_seconds=5.0)

    assert task.status == TaskStatus.RUNNING
    assert task.current_attempt == 1
    assert task.current_attempt_id == attempt_id
    assert task.assigned_node_id == "node-test-1"
    assert task.active_lease is not None
    assert task.active_lease.is_expired() is False

    # Expired check
    future = datetime.fromtimestamp(utc_now().timestamp() + 10.0, timezone.utc)
    assert task.active_lease.is_expired(now=future) is True
