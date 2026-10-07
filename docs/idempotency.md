# Idempotency

Idempotency prevents duplicate logical tasks when clients retry an HTTP submission.

## Header

Clients send:

    Idempotency-Key: checkout-2026-001

When a key is already known, Runtime.Submit returns the original task instead of creating a second task.

## Scope

The current implementation is process-local and backed by an in-memory synchronized map.

That means:

- it works correctly under concurrent requests in one process;
- it survives neither process restart nor multi-node deployment;
- a durable production implementation should store keys transactionally with task creation.

## Why it is separate

Idempotency answers "have I accepted this submission before?"

Task identity answers "what is this task?"

Execution RunID answers "which run happened?"

Keeping those three concepts distinct is what allows retries, recurring work and client retries to coexist.
