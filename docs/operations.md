# Operations

## Start

Run:

    go run ./cmd/taskmesh

The default service binds to :8080 and persists logical tasks to taskmesh-data.json.

## Submit

The simplest usable task is:

    curl -X POST http://localhost:8080/v1/tasks       -H 'Content-Type: application/json'       -d '{"name":"log","payload":{"message":"hello"}}'

The bundled log executor writes the payload to the application log.

## Observe

Useful endpoints:

    GET /health
    GET /ready
    GET /v1/metrics
    GET /v1/schedules
    GET /v1/dlq

For a specific execution:

    GET /v1/results/{runID}

## Scale

Set a startup size:

    TASKMESH_WORKERS=4

Change it without restarting:

    curl -X POST http://localhost:8080/v1/workers       -H 'Content-Type: application/json'       -d '{"workers":8}'

Enable queue-depth autoscaling:

    TASKMESH_AUTOSCALE_ENABLED=true

Then configure:

    TASKMESH_AUTOSCALE_MIN=1
    TASKMESH_AUTOSCALE_MAX=8
    TASKMESH_AUTOSCALE_HIGH=8
    TASKMESH_AUTOSCALE_LOW=0
    TASKMESH_AUTOSCALE_POLL=1s

## Persistence

The file repository is intended for single-node operation. Back up taskmesh-data.json according to the host's normal backup policy.

If the file is corrupted, the process intentionally fails during repository initialization rather than silently starting with an empty task set.

## Failure handling

A task can end in dead_letter when retries are exhausted.

Inspect:

    GET /v1/dlq

Recover one logical task:

    POST /v1/dlq
    {"task_id":"task-..."}

The DLQ entry is currently process-local. A restart clears the in-memory DLQ even though the task's latest logical status is durable. Durable DLQ storage is therefore part of the next persistence phase.

## Shutdown

TaskMesh listens for SIGINT and SIGTERM.

Shutdown sequence:

1. cancel runtime context;
2. cancel active execution contexts;
3. stop scheduler and autoscaler loops;
4. stop worker intake;
5. wait for workers to exit;
6. ask net/http to finish in-flight requests within the bounded shutdown timeout.

## Single-node limitation

The current executable is deliberately single-node.

It does not yet coordinate several TaskMesh processes against one shared queue. Do not run multiple instances against the same task data file.

A distributed deployment needs:

- shared durable task storage;
- atomic task claiming/leases;
- idempotent execution ownership;
- distributed schedule ownership or partitioning;
- durable execution history;
- shared DLQ;
- leader/lease handling for recurrence.

Those are architectural extensions, not environment variables.
