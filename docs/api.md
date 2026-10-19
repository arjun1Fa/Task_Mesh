# HTTP API

TaskMesh exposes liveness endpoints, a versioned orchestration API and legacy compatibility routes.
Api egegegegegegeggegege

## Health

### GET /health

Returns:

~~~json
{"status":"ok"}
~~~

### GET /ready

Returns the current worker target:

~~~json
{"status":"ready","workers":4}
~~~

## Create tasks

### POST /v1/tasks

The request body uses friendly transport formats for time and duration values.

~~~json
{
  "name": "log",
  "payload": {"message": "hello"},
  "id": "optional-client-id",
  "scheduled_at": "2030-01-01T12:00:00Z",
  "repeat_every": "5m",
  "max_attempts": 3,
  "timeout": "30s",
  "priority": 10,
  "metadata": {"source": "demo"}
}
~~~

Rules:

- name is required.
- id is optional; TaskMesh generates one when absent.
- scheduled_at is RFC3339.
- repeat_every and timeout use Go duration syntax.
- recurring tasks require scheduled_at.
- priority is higher-first; equal priorities preserve insertion order.
- Idempotency-Key is optional. Reusing a key returns the original logical task.

Normal creation returns 201 Created. A reused idempotency key returns 200 OK.

### GET /v1/tasks

Returns the current logical-task records.

### GET /v1/tasks/{id}

Returns one logical task.

## Dynamic task control

### POST /v1/tasks/{id}/schedule

Creates/replaces the task schedule.

~~~json
{
  "scheduled_at": "2030-01-01T12:00:00Z",
  "repeat_every": "1h"
}
~~~

Omit repeat_every for one-shot work.

### POST /v1/tasks/{id}/reschedule

Moves an existing scheduled task.

~~~json
{"scheduled_at":"2030-01-01T13:30:00Z"}
~~~

### POST /v1/tasks/{id}/cancel

Cancels a scheduled or active task.

~~~json
{"reason":"user request"}
~~~

## Scheduling inspection

### GET /v1/schedules

Returns the count and pending scheduler entries.

## Worker control

### GET /v1/workers

Returns the worker target.

### POST /v1/workers

Changes the target worker count:

~~~json
{"workers":8}
~~~

The value must be positive.

## Dead-letter queue

### GET /v1/dlq

Returns dead-letter task entries.

### POST /v1/dlq

Requeues the first entry matching a logical task ID:

~~~json
{"task_id":"task-123"}
~~~

## Results

### GET /v1/results/{runID}

Returns one recent execution result:

~~~json
{
  "TaskID": "task-123",
  "RunID": "run-...",
  "Attempt": 2,
  "StartedAt": "2030-01-01T12:00:00Z",
  "FinishedAt": "2030-01-01T12:00:01Z",
  "Status": "succeeded",
  "Error": ""
}
~~~

RunID is execution-level; task ID is logical-task-level.

## Metrics

### GET /v1/metrics

Returns process-local runtime values:

- workers
- queue_depth
- scheduled
- dead_letter

## Errors

All API errors use:

~~~json
{"error":"human-readable message"}
~~~

Bad JSON, invalid durations, invalid RFC3339 timestamps and invalid task fields return 400.

Unknown task IDs return 404 where the endpoint can distinguish them.

## Legacy compatibility

GET/POST /tasks and GET /task?id=... remain available for the original prototype. New clients should use the /v1 namespace.
