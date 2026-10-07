# Observability

The observability package contains small process-local metric primitives and event types. The runtime currently uses counters for lifecycle events and exposes basic gauges through GET /v1/metrics.

## Counters

Counter is backed by atomic.Int64 and supports:

- Inc
- Add
- Value

The runtime protects access to the counter registry with its own mutex before creating or reading counters.

## Gauges

Gauge is the complementary mutable numeric value used by the package. Runtime queue depth, worker count and DLQ size are exposed directly as a metrics response rather than pushed into the gauge registry.

## Event model

Event carries:

- Name
- TaskID
- Message

The runtime emits event names such as task.submitted, task.retrying, task.scheduled_due, task.canceled and task.dead_lettered.

The current executable does not publish those events to an external event bus. The type is intentionally small so a sink can be connected later.

## HTTP metrics

GET /v1/metrics returns:

    workers
    queue_depth
    scheduled
    dead_letter

These are point-in-time process-local values, not a replacement for Prometheus or OpenTelemetry.

## Future distributed observability

A production deployment should attach request IDs, correlation IDs, durable execution IDs and external metrics/traces to the same lifecycle events.
