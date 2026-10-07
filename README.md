# TaskMesh

TaskMesh is a Go task-orchestration service that accepts work over HTTP, persists task state, schedules delayed and recurring jobs, dispatches work through a priority-aware queue, executes handlers through a dynamically resizable worker pool, retries failures, supports cancellation and idempotency, and moves exhausted work to a dead-letter queue.

The repository is intentionally built around small interfaces so the transport, storage, scheduler, queue and executor implementations can evolve independently.

## Runtime at a glance

```text
                         ┌──────────────────────┐
                         │      HTTP Client     │
                         └──────────┬───────────┘
                                    │
                           POST /v1/tasks
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      API Server      │
                         └──────────┬───────────┘
                                    │
                         TaskService contract
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │      Runtime / Orchestrator  │
                    └───────┬─────────┬────────────┘
                            │         │
                   future/recurring   │ immediate
                            │         │
                            ▼         ▼
                     ┌──────────┐  ┌──────────────┐
                     │ Scheduler│  │ PriorityQueue│
                     └────┬─────┘  └──────┬───────┘
                          │ due             │
                          └───────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │ Dynamic Worker   │
                         │      Pool        │
                         └────────┬─────────┘
                                  │
                         registry lookup
                                  │
                                  ▼
                            Task Executor
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                  retry       succeeded       DLQ
                    │                           │
                    └────────────┬──────────────┘
                                 ▼
                          persisted task state
```

## What is implemented

| Capability | Status | Where |
|---|---|---|
| Task lifecycle | Implemented | `internal/core` |
| HTTP task submission | Implemented | `internal/api` |
| Idempotent submission | Implemented | `internal/idempotency` + runtime |
| Priority-aware queue | Implemented | `internal/queue/priority.go` |
| Delayed scheduling | Implemented | `internal/scheduler` |
| Recurring interval scheduling | Implemented | `internal/scheduler` + runtime |
| Live rescheduling | Implemented | runtime/API |
| Scheduled-task cancellation | Implemented | runtime/API |
| Dynamic worker resizing | Implemented | `internal/worker/pool.go` |
| Queue-driven autoscaling | Implemented | `internal/runtime` |
| Retry/backoff | Implemented | `internal/retry` + runtime |
| Dead-letter queue | Implemented | `internal/dlq` |
| Result lookup | Implemented | runtime/API |
| Durable single-node storage | Implemented | `internal/storage/file.go` |
| Startup recovery | Implemented | runtime |
| Health/readiness/metrics | Implemented | API |
| Graceful shutdown | Implemented | worker pool + executable |
| Authentication primitives | Present | `internal/auth` |
| Multi-node distributed coordination | Not yet implemented | Future adapter boundary |

The default executable uses the JSON file repository for durable single-node deployments and registers a small `log` executor as an example. Applications are expected to register their own task handlers.

## Quick start

Requirements: Go 1.23+.

```bash
go test ./...
go run ./cmd/taskmesh
```

The server listens on `http://localhost:8080` by default and stores task state in `taskmesh-data.json`.

Create an immediate task:

```bash
curl -X POST http://localhost:8080/v1/tasks   -H 'Content-Type: application/json'   -d '{"name":"log","payload":{"message":"hello TaskMesh"},"priority":10}'
```

Create a task for later:

```bash
curl -X POST http://localhost:8080/v1/tasks   -H 'Content-Type: application/json'   -d '{"name":"log","payload":{"message":"run later"},"scheduled_at":"2030-01-01T12:00:00Z"}'
```

Create a recurring task:

```bash
curl -X POST http://localhost:8080/v1/tasks   -H 'Content-Type: application/json'   -d '{"name":"log","payload":{"message":"heartbeat"},"scheduled_at":"2030-01-01T12:00:00Z","repeat_every":"1m"}'
```

Scale workers while the process is running:

```bash
curl -X POST http://localhost:8080/v1/workers   -H 'Content-Type: application/json'   -d '{"workers":8}'
```

Cancel a task:

```bash
curl -X POST http://localhost:8080/v1/tasks/TASK_ID/cancel   -H 'Content-Type: application/json'   -d '{"reason":"no longer needed"}'
```

## Documentation

Start with [the documentation index](docs/README.md).

For implementation-level understanding, read these in order:

1. [Architecture](docs/architecture.md)
2. [Runtime and orchestration](docs/runtime.md)
3. [Codebase guide](docs/codebase.md)
4. [HTTP API](docs/api.md)
5. [Scheduling](docs/scheduling.md)
6. [Workers](docs/workers.md)
7. [Retries](docs/retries.md)
8. [Storage](docs/storage.md)
9. [Operations](docs/operations.md)

## Development model

The codebase follows a simple rule: domain objects describe state, interfaces define boundaries, and the runtime coordinates state transitions. Transport code should not contain business logic, and worker handlers should not know how tasks were submitted.

The most important end-to-end path is:

`HTTP → TaskService → Runtime → Scheduler/Queue → WorkerPool → Registry Executor → Runtime state transition → Repository`.

## License

MIT
