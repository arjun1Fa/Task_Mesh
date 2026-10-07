# Runtime and orchestration

`internal/runtime/runtime.go` is the central coordinator.

## Construction

`runtime.New` receives:

- a `TaskRepository`
- a `TaskQueue`
- an executor `Registry`
- runtime configuration

It creates the scheduler, dead-letter queue and idempotency store and then builds a worker pool whose executor callback is `Runtime.execute`.

That callback is the key boundary: the worker pool knows nothing about retry policy, task state or persistence. It simply asks the runtime to execute a task.

## Submission flow

`Runtime.Submit` performs these steps:

1. Generate an ID when the caller omitted one.
2. Validate the task.
3. Reject submission when the runtime is stopped.
4. Resolve an idempotency key, if present.
5. Fill creation time and default timeout/attempt values.
6. Validate recurring-task requirements.
7. Persist a scheduled task and register it with the scheduler, or persist and enqueue an immediate task.
8. Record the idempotency key.
9. Emit a submission metric.

The logical task receives a new `RunID` before its first execution.

## Scheduled execution

The scheduler ticker periodically calls `Scheduler.Due`.

For every due task, `enqueueScheduled`:

1. checks whether the logical task was canceled;
2. creates a fresh `RunID`;
3. marks the occurrence queued in storage;
4. sends it to the ready queue.

Recurring schedules remain inside the scheduler while the current occurrence executes.

## Execution flow

`Runtime.execute`:

1. checks cancellation;
2. looks up the named handler;
3. creates an execution timeout;
4. records the active RunID;
5. executes attempts up to `MaxAttempts`;
6. persists `running` and `retrying` transitions;
7. waits for retry backoff between attempts;
8. records a `TaskResult`;
9. moves exhausted failures into the DLQ.

Unknown executor names fail as normal task executions rather than crashing the worker process.

## Cancellation

Scheduled cancellation removes the task from the scheduler and persists `canceled`.

For a running task, the runtime looks up the active RunID and cancels its context. The current public `Executor` interface does not receive that context directly, so application handlers that require cooperative cancellation should use a context-aware adapter when that API is introduced.

## Result history

Results are retained in memory by RunID, capped by `ResultHistoryMax`.

The repository stores the latest logical-task state. Result history records execution-level facts such as attempt number and timing. A production multi-node deployment would normally persist execution history separately.

## Startup recovery

`rehydrate` reconstructs runtime state from the repository before workers start consuming work:

- `scheduled` tasks are returned to the scheduler;
- `queued`, `running` and `retrying` tasks are requeued;
- terminal tasks are not revived.

This makes persisted lifecycle state the restart recovery source of truth.

## Autoscaling

The optional autoscale loop samples queue depth.

- At or above `HighWatermark`, it increases workers by one until `MaxWorkers`.
- At or below `LowWatermark`, it decreases workers by one until `MinWorkers`.

Direct worker resizing and autoscaling both operate on the same pool target.
