# Configuration

Configuration is resolved by internal/config.

The resolution order is:

1. built-in defaults;
2. environment variables;
3. startup validation.

Invalid integer, boolean or duration environment values fall back to the default rather than crashing configuration parsing.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| TASKMESH_ADDR | :8080 | HTTP listen address |
| TASKMESH_DATA_FILE | taskmesh-data.json | durable task-state file |
| TASKMESH_WORKERS | 4 | initial worker target |
| TASKMESH_RETRY_ATTEMPTS | 3 | default maximum attempts |
| TASKMESH_RETRY_BASE_DELAY | 1s | base retry delay |
| TASKMESH_SCHEDULER_POLL | 250ms | scheduler polling interval |
| TASKMESH_TASK_TIMEOUT | 30s | default task execution timeout |
| TASKMESH_AUTOSCALE_ENABLED | false | enable queue-depth autoscaling |
| TASKMESH_AUTOSCALE_MIN | 1 | autoscale lower bound |
| TASKMESH_AUTOSCALE_MAX | 8 | autoscale upper bound |
| TASKMESH_AUTOSCALE_HIGH | 8 | queue depth that triggers scale-up |
| TASKMESH_AUTOSCALE_LOW | 0 | queue depth at/below which scale-down is allowed |
| TASKMESH_AUTOSCALE_POLL | 1s | autoscaler polling interval |

## Python TaskMesh Runtime & Wireless Configuration

In the Python system (`taskmesh/core/config.py`), configuration is managed via Pydantic settings with environment variable overrides:

### Wireless & Transport Settings

| Environment Variable / Config Key | Default | Description |
|---|---|---|
| `TASKMESH_MAX_PAYLOAD_SIZE_BYTES` | `52428800` (50 MB) | Maximum accepted binary inference payload size before early rejection |
| `TASKMESH_CHUNK_SIZE_BYTES` | `65536` (64 KB) | WebSocket binary framing chunk size for streaming transport |
| `TASKMESH_ENABLE_DISCOVERY` | `true` | Enables background UDP broadcast discovery beacon |
| `TASKMESH_DISCOVERY_PORT` | `37020` | UDP port used for LAN node discovery beacons |
| `TASKMESH_IS_LOCAL` | `false` | Marks a node agent as physically local to the orchestrator/client |
| `TASKMESH_LAN_IP` | `null` (auto-detected) | Overrides automatic LAN IP resolution for node advertising |
| `TASKMESH_DISCOVERY_BEACON_INTERVAL_S`| `5.0` | Interval in seconds between UDP broadcast beacons |
| `TASKMESH_PROBE_INTERVAL_S` | `3.0` | Interval in seconds for WebSocket ping/pong RTT measurement |

### Core Orchestrator Settings

| Environment Variable / Config Key | Default | Description |
|---|---|---|
| `TASKMESH_HOST` | `0.0.0.0` | IP interface binding address for the FastAPI server |
| `TASKMESH_PORT` | `8000` | HTTP/WebSocket listen port |
| `TASKMESH_SCHEDULER_MODE` | `adaptive` | Scheduling algorithm (`adaptive`, `round_robin`, `least_loaded`, `highest_bid`) |
| `TASKMESH_HEARTBEAT_TIMEOUT_SECONDS` | `10.0` | Time before an unresponsive node is marked OFFLINE |
| `TASKMESH_LEASE_DURATION_SECONDS` | `30.0` | Duration of task execution lease before reassignment |
| `TASKMESH_MAX_RETRIES` | `3` | Maximum automatic retries before moving task to Dead-Letter Queue (DLQ) |

