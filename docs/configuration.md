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

## Validation

Config.Valid requires:

- non-empty data and HTTP paths;
- positive worker count;
- positive retry attempts and delay;
- positive scheduler poll and task timeout;
- a valid autoscale range and polling interval.

Runtime normalization still provides safety defaults when Runtime is constructed directly in code rather than through config.Resolve.
