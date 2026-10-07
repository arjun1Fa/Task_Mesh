# Dead-letter queue

The DLQ is implemented in internal/dlq.

## When a task enters the DLQ

A task is sent to the DLQ after its configured attempts are exhausted.

The repository state is moved to dead_letter at the same time.

Each DLQ Item contains:

- the logical Task snapshot;
- the number of attempts;
- the failure reason.

## Why snapshots are copied

Queue and storage APIs clone task data. DLQ also clones task data on insertion and listing.

This prevents a caller from mutating internal payload or metadata through a returned object.

## Recovery

Recovery returns the original task payload through dlq.Recover and the runtime gives it a fresh RunID before requeueing.

Recovery is explicit. A terminal dead-letter task is not automatically retried after restart.

## Operational purpose

The DLQ is where operators inspect failures that automation could not resolve.

A production deployment should add durable DLQ state, recovery audit records and an operator authorization layer.
