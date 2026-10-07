"""Retry policies, backoff calculation, and jitter logic."""

import random
from typing import Tuple

from taskmesh.core.models import RetryPolicy, Task


class RetryDecision:
    def __init__(self, should_retry: bool, delay_seconds: float, attempt: int, reason: str = ""):
        self.should_retry = should_retry
        self.delay_seconds = delay_seconds
        self.attempt = attempt
        self.reason = reason


def compute_backoff(policy: RetryPolicy, attempt: int) -> float:
    """Calculates exponential backoff with full jitter."""
    if attempt <= 0:
        return 0.0

    # base * 2^(attempt - 1)
    delay = policy.base_delay_seconds * (2 ** (attempt - 1))
    delay = min(delay, policy.max_delay_seconds)

    if policy.jitter and delay > 0:
        # Full jitter: uniformly distributed between 0 and calculated backoff
        delay = random.uniform(0.5 * delay, delay)

    return max(0.0, delay)


def evaluate_retry(task: Task, error_message: str) -> RetryDecision:
    """Evaluates whether a task should be retried or moved to DLQ."""
    policy = task.retry_policy
    next_attempt = task.retry_count + 1

    if next_attempt > policy.max_attempts:
        return RetryDecision(
            should_retry=False,
            delay_seconds=0.0,
            attempt=next_attempt,
            reason=f"Exhausted maximum retry attempts ({policy.max_attempts}): {error_message}"
        )

    delay = compute_backoff(policy, next_attempt)
    return RetryDecision(
        should_retry=True,
        delay_seconds=delay,
        attempt=next_attempt,
        reason=f"Attempt {next_attempt}/{policy.max_attempts} after error: {error_message}"
    )
