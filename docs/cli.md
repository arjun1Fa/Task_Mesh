# taskmeshctl

taskmeshctl is intentionally a thin HTTP client.

## Design

The CLI is split into:

- argument parsing;
- command definitions;
- help text;
- request construction;
- HTTP execution;
- response handling.

The CLI should not duplicate runtime business logic. When scheduling or worker behavior changes, the runtime/API should be updated first and the CLI should remain a transport client.

## Typical responsibilities

Argument parsing converts command-line values into typed request values.

Request code adds the TaskMesh HTTP base URL and sends the appropriate method/body.

Command code decides which endpoint to call.

## Extension rule

When adding a new command:

1. define the command in internal/cli/commands.go or taskmesh/cli/main.py;
2. add parsing tests;
3. add request tests;
4. keep the endpoint contract documented in docs/api.md;
5. avoid implementing orchestration policy inside the CLI.

---

## Wireless Inference Commands

The Python CLI (`taskmesh` and `taskmeshctl`) provides dedicated commands for wireless offloading:

### 1. `taskmesh submit-image`
Submits a local image file directly to the orchestrator as a multipart binary payload.
```bash
taskmesh submit-image --file frame.jpg --policy wireless_allowed --priority 5 --gpu
```
Options:
- `--file <path>`: Local JPEG/PNG image path.
- `--policy <policy>`: `local_only`, `wireless_allowed`, or `remote_allowed` (default: `wireless_allowed`).
- `--priority <int>`: Priority integer (default: `5`).
- `--gpu / --no-gpu`: Flag requiring hardware GPU execution.

### 2. `taskmesh node discover` / `taskmeshctl discover`
Listens for local-network UDP discovery beacons on port 37020 and prints active peer details.
```bash
taskmesh node discover --timeout 3.0 --port 37020
```

### 3. `taskmesh node connect`
Convenience wrapper to register or connect a node agent to a discovered orchestrator IP:
```bash
taskmesh node connect --orchestrator ws://192.168.1.100:8000 --node-id gpu-worker-1
```

