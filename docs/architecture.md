# Architecture

TaskMesh is organized around a coordinator-style runtime with deliberately narrow interfaces.

## Component ownership

| Component | Owns | Does not own |
|---|---|---|
| `internal/core` | task data, lifecycle states, validation, result types | network, storage, scheduling |
| `internal/api` | HTTP decoding, routing, response formatting | task execution decisions |
| `internal/runtime` | orchestration and lifecycle transitions | business task implementation |
| `internal/scheduler` | time-based eligibility | task execution |
| `internal/queue` | ready-task ordering and waiting | persistence or retries |
| `internal/worker` | concurrency and handler registry | task admission policy |
| `internal/retry` | attempt count and backoff calculation | task persistence |
| `internal/storage` | task state durability | worker scheduling |
| `internal/dlq` | failed-task isolation and recovery payload | retry decision |
| `internal/idempotency` | submission-key lookup | task execution |
| `internal/observability` | counters/events | orchestration decisions |
| `internal/config` | typed startup configuration | application logic |

## End-to-end lifecycle

~~~text
queued
  |
  +-------- scheduled --------+
  |                           | due
  |                           v
  +-----------------------> queued
                              |
                              v
                           running
                              |
                 +------------+------------+
                 |                         |
              success                    error
                 |                         |
                 v                         v
             succeeded                 retrying
                                           |
                                  attempts remain?
                                      /                                           yes       no
                                     |         |
                                     +-- run   v
                                           dead_letter
~~~

Cancellation may terminate a scheduled task before it becomes queued. A running task is associated with an active RunID so the runtime can cancel its execution context.

## Why RunID exists

ID identifies the logical task. RunID identifies one execution instance. This is required for recurring tasks, where the same logical task can fire many times.

## Scheduler boundary

The scheduler answers one question: "Which scheduled tasks are due now?"

It does not execute work and does not know about HTTP. The runtime receives due tasks and decides how they enter the ready queue.

Recurring entries remain in the scheduler after an occurrence is emitted. The next occurrence is advanced relative to the current scheduler clock, preventing an unbounded burst after a long pause.

## Queue boundary

The TaskQueue interface is intentionally small:

- Enqueue
- Dequeue
- Len

BlockingTaskQueue adds DequeueContext. The worker pool detects that optional capability and uses it to wait efficiently instead of spinning.

The managed runtime uses PriorityQueue. Higher priorities are dequeued first; equal priorities retain FIFO order.

## Worker boundary

An Executor handles one task:

~~~go
type Executor interface {
    Execute(core.Task) error
}
~~~

The runtime wraps execution with timeout, retry, cancellation bookkeeping and durable state transitions. Executor implementations therefore stay focused on business logic.

## Persistence and recovery

The runtime persists task state before placing work into the scheduler or queue. On startup it scans repository state and rebuilds:

- scheduled tasks into the scheduler;
- queued, running and retrying tasks into the ready queue;
- terminal tasks as-is.

This is a deliberate recovery strategy for a single-node runtime.

## Dynamic behavior

Direct scaling is performed through POST /v1/workers.

Autoscaling is optional. It samples queue depth and adjusts the worker target inside MinWorkers and MaxWorkers using HighWatermark and LowWatermark.

Scheduling is dynamic through schedule, reschedule and cancellation operations.

## Distributed boundary

The current implementation is a complete single-process execution engine. It is not a multi-node cluster: there is no leader election, distributed lease, shared queue claim protocol or consensus layer.

Those concerns should be implemented as explicit adapters around durable storage and queue boundaries rather than hidden inside the core runtime.
