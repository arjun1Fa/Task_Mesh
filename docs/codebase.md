# Codebase guide

This page maps the repository to the responsibilities a developer should understand before changing code.

## Entry point

### cmd/taskmesh/main.go
Bootstraps configuration, durable storage, priority queue, executor registry, runtime, HTTP server and signal-based graceful shutdown.

## Core domain

### internal/core/task.go
Defines the durable logical task, including stable ID, per-run ID, payload, lifecycle status, schedule, recurrence, retry settings, timeout, priority and metadata. Clone prevents shared slices/maps/pointers from being mutated by callers.

### internal/core/status.go
Defines lifecycle states and Terminal.

### internal/core/task_validation.go
Contains shared validation and normalization rules.

### internal/core/result.go
Defines execution-level TaskResult.

### internal/core/cancel.go
Core cancellation value object.

### internal/core/metadata.go
Core metadata value object.

### internal/core/lifecycle.go
Lifecycle helper functions.

## Queue

### internal/queue/queue.go
TaskQueue interface: Enqueue, Dequeue, Len.

### internal/queue/blocking.go
Optional BlockingTaskQueue interface with context-aware waiting.

### internal/queue/fifo.go
Simple thread-safe FIFO implementation.

### internal/queue/priority.go
Heap-backed default queue. Higher Priority executes first; equal priorities retain FIFO order.

## Scheduler

### internal/scheduler/item.go
One scheduled occurrence plus recurrence interval.

### internal/scheduler/scheduler.go
Thread-safe schedule storage, ordering, due detection, recurrence advancement, cancellation and rescheduling.

### internal/scheduler/clock.go
Clock seam for deterministic tests.

### internal/scheduler/ticker.go
Periodic loop that emits due tasks to the runtime.

### internal/scheduler/config.go, limits.go, validation.go, snapshot.go
Configuration, capacity/error, validation and snapshot helpers.

## Worker subsystem

### internal/worker/executor.go
Executor interface and ExecutorFunc adapter.

### internal/worker/registry.go
Thread-safe task-name to executor registry.

### internal/worker/pool.go
Worker goroutine lifecycle, dynamic Resize, blocking queue consumption and graceful shutdown.

### internal/worker/pool_runtime.go
Detached pool lifecycle helper.

### internal/worker/runtime.go
Small worker execution helper retained for isolated tests.

### internal/worker/retry_executor.go
Convenience adapter around retry.Runner.

### internal/worker/result.go, errors.go, safe_executor.go
Worker result and execution-safety primitives.

### internal/worker/cancel.go, shutdown.go
Worker lifecycle helpers.

## Retry

### internal/retry/policy.go
Attempt limits and base delay.

### internal/retry/backoff.go
Backoff calculation.

### internal/retry/decision.go
Retry decision.

### internal/retry/errors.go
Retry sentinels.

### internal/retry/runner.go
Reusable context-aware retry loop.

### internal/retry/jitter.go, metrics.go
Optional retry jitter and metrics primitives.

## Runtime

### internal/runtime/runtime.go
The orchestration brain. It connects persistence, idempotency, scheduling, queueing, workers, executor lookup, timeouts, cancellation, retries, results, DLQ, autoscaling and startup recovery.

The execution boundary is Runtime.execute. That keeps workers generic and puts lifecycle policy in one place.

## API

### internal/api/server.go
Binds a TaskService to net/http. NewServer preserves the original lightweight test constructor; NewRuntimeServer binds the complete runtime.

### internal/api/routes.go
Route registration.

### internal/api/handlers.go
Task request parsing, time/duration parsing, transport response formatting and compatibility endpoints.

### internal/api/orchestration_handlers.go
Schedule inspection, worker scaling, DLQ recovery, result lookup and metrics.

### internal/api/service.go
Transport-independent task service contract.

### internal/api/response.go, validation.go
JSON response/error and path helpers.

### internal/api/middleware.go, middleware_chain.go
Logging and middleware composition.

### internal/api/request_id.go, correlation.go
Request/correlation identifiers.

### internal/api/limits.go, methods.go, cors.go, security_headers.go
API hardening helpers.

## Storage

### internal/storage/repository.go
TaskRepository boundary.

### internal/storage/memory.go
Thread-safe test repository.

### internal/storage/file.go
Durable JSON repository with atomic replacement of the data file.

### internal/storage/sqlite.go
Explicit disabled adapter seam. It returns a clear unsupported error instead of pretending to be durable.

### internal/storage/insert.go, update.go, query.go, schema.go
Relational adapter fragments from the earlier design.

### internal/storage/transaction.go
Transaction value object.

### internal/storage/cancel.go, errors.go, health.go
Storage lifecycle/error helpers.

## Idempotency

### internal/idempotency/key.go
Key value type.

### internal/idempotency/store.go
Thread-safe process-local key-to-task store.

### internal/idempotency/result.go
Idempotency result type.

## Dead-letter queue

### internal/dlq/item.go
DLQ entry snapshot.

### internal/dlq/queue.go
Thread-safe DLQ storage.

### internal/dlq/recover.go
Recovery conversion back to a task.

## Observability

### internal/observability/counter.go
Atomic counter.

### internal/observability/gauge.go
Gauge primitive.

### internal/observability/registry.go
Metric registry.

### internal/observability/events.go
Lifecycle event type.

### internal/observability/sink.go, memory_sink.go
Event sink abstraction and in-memory sink.

### internal/observability/log.go, health.go
Logging/health helpers.

## Configuration

### internal/config/config.go
Full runtime configuration model.

### internal/config/defaults.go
Safe defaults.

### internal/config/env.go
Typed environment readers.

### internal/config/runtime.go
Environment resolution.

### internal/config/validation.go
Startup validation.

## CLI and versioning

### cmd/taskmeshctl/main.go, version.go
CLI entry point and version reporting.

### internal/cli/*
CLI argument parsing, command definitions, help text, request helpers and tests.

### internal/version/*
Application version boundary.

## Tests and benchmarks

Package tests live beside implementations as *_test.go files.

Cross-package flow tests live under internal/integration.

Queue benchmarks live under benchmarks.

tests/README.md contains additional testing guidance.

## The most useful trace to learn the system

For task submission, trace:

HTTP route
→ API request decoder
→ TaskService
→ Runtime.Submit
→ repository
→ scheduler OR priority queue
→ worker pool
→ Runtime.execute
→ executor registry
→ business Executor
→ retry/state transition
→ repository/result/DLQ.

For dynamic scheduling, trace:

POST /v1/tasks/{id}/schedule
→ Runtime.Schedule
→ Scheduler.Schedule
→ repository.

For rescheduling:

POST /v1/tasks/{id}/reschedule
→ Runtime.Reschedule
→ Scheduler.Reschedule
→ repository.

For worker scaling:

POST /v1/workers
→ Runtime.ScaleWorkers
→ Pool.Resize.

For autoscaling:

queue depth
→ Runtime.autoscale
→ Pool.Resize.

## Ownership rule

When modifying the project, put decisions in the layer that owns them:

- task schema/lifecycle: core
- HTTP translation: api
- orchestration decisions: runtime
- timing: scheduler
- ready-task ordering: queue
- concurrency: worker
- backoff math: retry
- durable state: storage
- failed-work isolation: dlq
- duplicate requests: idempotency
- counters/events: observability
- environment values: config

This keeps the system understandable as it grows.
