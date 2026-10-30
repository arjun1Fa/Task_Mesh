# TaskMesh — Current Implementation Status

## 1. Subsystem Implementation Matrix

| Subsystem / Component | Implementation Status | Code Evidence | Real Limitations & Constraints |
|---|---|---|---|
| **Domain Models & Enums** | **Implemented & Tested** | [`taskmesh/core/models.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/models.py), [`taskmesh/core/enums.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/enums.py) | In-memory representations; schema migrations must be handled manually. |
| **Priority Queue** | **Implemented & Tested** | [`taskmesh/queue/priority.py`](file:///C:/Malenia/TASK_MESH/taskmesh/queue/priority.py) | In-memory heap; queue contents are reloaded from SQLite upon process restart. |
| **Durable Task Persistence** | **Implemented & Tested** | [`taskmesh/persistence/repositories.py`](file:///C:/Malenia/TASK_MESH/taskmesh/persistence/repositories.py) | SQLite-backed with single global lock; adequate for small/medium clusters, but SQLite write contention is a bottleneck at > 1,000 tasks/s. |
| **PostgreSQL Persistence** | **Designed / Planned** | [`TaskRepository` protocol boundary](file:///C:/Malenia/TASK_MESH/taskmesh/persistence/repositories.py) | Abstract interface is ready, but concrete async PostgreSQL / asyncpg driver is not yet implemented. |
| **Node Registry & Health** | **Implemented & Tested** | [`taskmesh/cluster/registry.py`](file:///C:/Malenia/TASK_MESH/taskmesh/cluster/registry.py) | In-memory dictionary; relies on orchestrator heartbeat loop (9s timeout). |
| **WebSocket Protocol** | **Implemented & Tested** | [`taskmesh/protocol/messages.py`](file:///C:/Malenia/TASK_MESH/taskmesh/protocol/messages.py) | Unencrypted `ws://` by default unless deployed behind a TLS reverse proxy. |
| **Adaptive Scheduler Pipeline** | **Implemented & Tested** | [`taskmesh/scheduler/adaptive.py`](file:///C:/Malenia/TASK_MESH/taskmesh/scheduler/adaptive.py) | Evaluates nodes in single-threaded async lock; sub-millisecond, but scales linearly with candidate node count. |
| **Deficit Round Robin (DRR)** | **Implemented & Tested** | [`taskmesh/fairness/drr.py`](file:///C:/Malenia/TASK_MESH/taskmesh/fairness/drr.py) | Verified bug fix: deficit increments occur only upon round exhaustion. Bounded memory per node. |
| **Contract-Net Bidding** | **Implemented & Tested** | [`taskmesh/bidding/contract_net.py`](file:///C:/Malenia/TASK_MESH/taskmesh/bidding/contract_net.py) | 5 normalized factors; relies on accurate telemetry reports from nodes. |
| **MWU Online Adaptation** | **Implemented & Tested** | [`taskmesh/learning/mwu.py`](file:///C:/Malenia/TASK_MESH/taskmesh/learning/mwu.py) | Fast exponential loss updates, but sensitive to `eta` learning rate hyperparameter. |
| **Tabular Q-Learning** | **Implemented & Tested** | [`taskmesh/learning/qlearning.py`](file:///C:/Malenia/TASK_MESH/taskmesh/learning/qlearning.py) | Bounded to 27 states $\times$ 3 candidate-slot actions; cannot differentiate beyond top 3 candidates. |
| **Wireless Cost Estimator** | **Implemented & Tested** | [`taskmesh/wireless/estimator.py`](file:///C:/Malenia/TASK_MESH/taskmesh/wireless/estimator.py) | Estimates transfer time via EWMA RTT & bandwidth; does not measure packet loss or Wi-Fi channel airtime. |
| **UDP Broadcast Discovery** | **Implemented & Tested** | [`taskmesh/discovery/broadcast.py`](file:///C:/Malenia/TASK_MESH/taskmesh/discovery/broadcast.py) | Operates strictly within single broadcast domain (subnet); cannot cross VLANs or routers without relay. |
| **Binary Protocol (`TMCH`)** | **Implemented & Tested** | [`taskmesh/transport/binary_protocol.py`](file:///C:/Malenia/TASK_MESH/taskmesh/transport/binary_protocol.py) | 48-byte header, 64KB chunking, SHA-256 validation. Capped at 50MB payload size ceiling. |
| **Node Worker Pool** | **Implemented & Tested** | [`taskmesh/node/worker_pool.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/worker_pool.py) | In-process execution + ThreadPoolExecutor; no container or process sandboxing. |
| **Retry & Dead-Letter Queue** | **Implemented & Tested** | [`taskmesh/retry/runner.py`](file:///C:/Malenia/TASK_MESH/taskmesh/retry/runner.py), [`taskmesh/dlq/manager.py`](file:///C:/Malenia/TASK_MESH/taskmesh/dlq/manager.py) | Exponential backoff with jitter and manual API/CLI recovery. |
| **Intermediate Checkpoints** | **Implemented & Tested** | [`taskmesh/checkpoint/manager.py`](file:///C:/Malenia/TASK_MESH/taskmesh/checkpoint/manager.py) | Checkpoints streamed and reattached upon failure; currently stored in-memory in runtime. |
| **Primary/Standby Failover** | **Implemented & Tested** | [`taskmesh/orchestrator/runtime.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/runtime.py) | HTTP snapshot polling with auto-promotion; vulnerable to split-brain in asymmetric partitions. |
| **HMAC Security Layer** | **Implemented & Tested** | [`taskmesh/security/hmac_auth.py`](file:///C:/Malenia/TASK_MESH/taskmesh/security/hmac_auth.py) | HMAC-SHA256, sequence monotonicity, timestamp skew check; relies on shared cluster secret. |
| **CLI (`taskmeshctl`)** | **Implemented & Tested** | [`taskmesh/cli/main.py`](file:///C:/Malenia/TASK_MESH/taskmesh/cli/main.py) | Complete command suite for tasks, nodes, discovery, health, scheduler, and DLQ. |
| **Web Dashboard UI** | **Implemented & Tested** | [`taskmesh/orchestrator/static/index.html`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/static/index.html) | Vanilla HTML/CSS/JS served directly by FastAPI; real-time polling every 3 seconds. |

---

## 2. Technical Debt, Gaps & Architectural Weaknesses

### 2.1 Stale Documentation from Initial Go Scaffold
In the repository's early commit history (commits `dccc747` through `076a74f`), the project was initially conceived or prototyped in Go (`internal/core/task.go`, `cmd/taskmesh/main.go`). Several markdown files in `docs/` (`docs/codebase.md`, `docs/api.md`, `docs/workers.md`, `docs/retries.md`) still contain descriptions of Go files and net/http routes that do not exist. The actual implementation in Python (`taskmesh/`) is the primary source of truth.

### 2.2 SQLite Single-Writer Lock Contention
`SQLiteTaskRepository` uses a single `asyncio.Lock()` around database transactions. While SQLite is durable and zero-maintenance for local development and edge clusters (< 20 nodes), running benchmarks with hundreds of concurrent submissions causes thread lock contention. Replacing this with an asynchronous PostgreSQL backend (`asyncpg`) is a key priority.

### 2.3 Standby Asymmetric Split-Brain Risk
The warm-standby orchestrator promotes itself after 3 failed snapshot polling requests. If a network partition occurs where the primary can communicate with worker nodes but the standby cannot reach the primary, the standby could self-promote, resulting in two orchestrators attempting to manage the same cluster. Implementing a split-brain breaker or consensus quorum (Raft) is necessary for mission-critical deployments.

### 2.4 Lack of Sandboxing in Worker Execution
`WorkerPool` executes task handlers directly on the host machine. If an edge node accepts arbitrary user workloads, a malicious or buggy handler can consume infinite memory or access local disk files. Adding lightweight containerization (e.g. Docker / Podman / gVisor) is necessary for multi-tenant environments.

### 2.5 Test Environment Dependency Gap
`pyproject.toml` defines optional dependency group `test = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]`. However, in the default `.venv` environment, `pytest` is not pre-installed, requiring developers to run `pip install pytest pytest-asyncio` before executing tests.

