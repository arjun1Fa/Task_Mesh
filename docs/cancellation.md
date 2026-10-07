# Cancellation

Cancellation is implemented in internal/runtime and exposed through POST /v1/tasks/{id}/cancel.

## Scheduled cancellation

For a task waiting in the scheduler:

1. the runtime removes the schedule entry;
2. the logical task is persisted as canceled;
3. no future occurrence is emitted.

For recurring tasks, this also ends future occurrences.

## Queued cancellation

The ready queue does not support arbitrary removal because doing so would complicate ordering guarantees.

Instead the runtime persists canceled state. When the execution path sees that state, it refuses to execute the task.

## Running cancellation

The runtime keeps cancel functions indexed by RunID for active executions.

Canceling a running task calls the function and updates durable task state.

The current public Executor interface does not receive context.Context, so a business handler cannot yet observe the cancellation through the method signature. This is documented as a limitation rather than hidden.

## Restart semantics

Canceled is terminal. rehydrate never places canceled tasks back into the scheduler or queue.
