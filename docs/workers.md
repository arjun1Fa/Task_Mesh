# Workers

Workers live in internal/worker.

## Executor

The Executor interface contains one operation:

    Execute(core.Task) error

Executor implementations should contain business behavior only. They should not update task lifecycle state, push to the queue or implement HTTP concerns.

ExecutorFunc is an adapter that turns an ordinary function into an Executor.

## Registry

Registry maps a task name to exactly one Executor.

Register is concurrency-safe and rejects duplicate names. Replace is available when an application intentionally wants to swap a handler at runtime.

MustRegister is useful during startup because registration failure should stop bootstrap rather than create a partially configured service.

## Queue interaction

The Pool accepts the general TaskQueue interface.

When the queue also implements BlockingTaskQueue, workers call DequeueContext and sleep efficiently while idle.

The bundled PriorityQueue implements that capability.

## Worker lifecycle

Run starts the initial worker target.

Resize changes the target while the runtime remains online:

- increasing the target creates new goroutines;
- decreasing the target cancels worker contexts;
- worker goroutines exit through their context;
- the pool tracks them with a WaitGroup.

Run waits for worker goroutines during shutdown.

## Why the pool does not retry

Retry belongs to runtime orchestration, not the pool. Keeping the pool generic makes it reusable for tasks whose retry semantics differ.

The pool's only execution responsibility is: take a task, call its Executor, repeat until the worker context ends.

## Dynamic scaling

Direct scaling is exposed through POST /v1/workers.

Autoscaling in internal/runtime samples queue depth and calls the same Resize method. There is therefore one authoritative worker target.

For a distributed worker fleet, this local Resize operation would be replaced or supplemented by an external worker scheduler.
