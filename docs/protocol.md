# TaskMesh WebSocket Protocol Specification

TaskMesh nodes communicate with the Orchestrator via persistent WebSockets over `/v1/ws/nodes`.

## Protocol Envelope

All messages are exchanged as JSON text frames matching the `ProtocolMessage` model:

```json
{
  "protocol_version": "v1",
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "message_type": "heartbeat",
  "node_id": "node-alpha",
  "timestamp": "2026-10-08T00:00:00Z",
  "sequence_number": 42,
  "payload": {}
}
```

## Message Types

### 1. Connection & Lifecycle
- `register_node`: Sent by node immediately upon connection. Contains hardware specs (`cpu_cores`, `ram_total_mb`, `has_gpu`, `supported_handlers`, `tags`) and cluster `token`.
- `register_ack`: Returned by Orchestrator acknowledging registration or rejecting invalid credentials.
- `heartbeat`: Sent periodically by node (default: every 3s) containing current status and active task counts.
- `telemetry`: Sent periodically by node (default: every 5s) reporting CPU %, RAM %, GPU %, and latency.
- `node_drain`: Sent by Orchestrator requesting node to complete active tasks without accepting new ones.

### 2. Task Dispatch & Execution
- `task_assignment`: Sent by Orchestrator to assign a task attempt with lease expiration, payload, priority, and checkpoint state.
- `task_accepted`: Node acknowledges task acceptance.
- `task_rejected`: Node rejects task (e.g. if draining or overloaded).
- `task_started`: Node announces execution commencement.
- `task_progress`: Node streams float progress in `[0.0, 1.0]`.
- `task_checkpoint`: Node streams intermediate state checkpoints for fault-tolerant recovery.
- `task_completed`: Node returns `TaskResult` with status, output dict, and execution latency.
- `task_failed`: Node returns execution error string.
- `task_cancel`: Orchestrator transmits cancellation signal down to node worker pool.
- `task_cancelled`: Node confirms task cancellation.
