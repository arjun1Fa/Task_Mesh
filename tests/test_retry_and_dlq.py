"""Unit tests for Retry Policies and Dead Letter Queue."""

import pytest
from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import RetryPolicy, Task
from taskmesh.dlq.manager import DLQManager
from taskmesh.retry.runner import compute_backoff, evaluate_retry


def test_retry_backoff_calculation():
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0, max_delay_seconds=10.0, jitter=False)
    # Attempt 1: 1 * 2^0 = 1.0s
    d1 = compute_backoff(policy, attempt=1)
    assert d1 == 1.0

    # Attempt 2: 1 * 2^1 = 2.0s
    d2 = compute_backoff(policy, attempt=2)
    assert d2 == 2.0

    # Attempt 3: 1 * 2^2 = 4.0s
    d3 = compute_backoff(policy, attempt=3)
    assert d3 == 4.0


def test_retry_exhaustion():
    policy = RetryPolicy(max_attempts=2, base_delay_seconds=0.5, jitter=False)
    task = Task(task_type="log", retry_policy=policy, retry_count=0)

    # First failure -> retry allowed
    dec1 = evaluate_retry(task, "Network glitch")
    assert dec1.should_retry is True
    assert dec1.attempt == 1

    # Second failure
    task.retry_count = 1
    dec2 = evaluate_retry(task, "Network glitch again")
    assert dec2.should_retry is True
    assert dec2.attempt == 2

    # Third failure -> max attempts exceeded
    task.retry_count = 2
    dec3 = evaluate_retry(task, "Fatal error")
    assert dec3.should_retry is False


@pytest.mark.asyncio
async def test_dlq_add_and_recovery():
    dlq = DLQManager()
    task = Task(id="bad-task", task_type="log", retry_count=3)

    await dlq.add(task, final_error="Permanent database failure")
    assert task.status == TaskStatus.DLQ

    items = await dlq.list_items()
    assert len(items) == 1
    assert items[0].task.id == "bad-task"

    # Recover task
    recovered = await dlq.recover("bad-task")
    assert recovered is not None
    assert recovered.status == TaskStatus.PENDING
    assert recovered.retry_count == 0

    # DLQ should now be empty
    assert len(await dlq.list_items()) == 0
