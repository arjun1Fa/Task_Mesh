# TaskMesh — Codebase Deep Dive & Navigation Guide

## 1. Directory Structure

```text
TASK_MESH/
├── benchmarks/                        # Algorithmic & distributed benchmark suites
│   ├── benchmark_schedulers.py        # Microbenchmark comparing isolated scheduler latency & allocations
│   ├── benchmark_distributed.py       # Real multi-process end-to-end WebSocket benchmark
│   ├── benchmark_wireless.py          # Wireless offloading vs local computation benchmarks
│   ├── reconcile_learning_ablations.py# Repeatability study verifying Q-learning & MWU ablations
│   └── experiment_runs/               # Raw empirical JSON telemetry from automated trials
├── docs/                              # Project documentation & specifications
│   └── project-knowledge/            # Complete onboarding knowledge extraction suite (this documentation)
├── scripts/
│   └── manual_wifi_test.py            # Physical 2-machine Wi-Fi verification script
├── taskmesh/                          # Primary TaskMesh Python package
│   ├── bidding/
│   │   └── contract_net.py            # 5-factor auction suitability bidding
│   ├── checkpoint/
│   │   └── manager.py                 # Task checkpoint storage and re-attachment
│   ├── cli/
│   │   └── main.py                    # taskmeshctl CLI tool implementation
│   ├── cluster/
│   │   ├── dev_cluster.py             # Single-command local multi-process cluster launcher
│   │   └── registry.py                # Thread-safe node registry & WebSocket socket mappings
│   ├── core/
│   │   ├── config.py                  # OrchestratorConfig & NodeConfig via Pydantic
│   │   ├── enums.py                   # Enums: TaskStatus, NodeStatus, SchedulerMode, MessageType
│   │   ├── errors.py                  # Domain exceptions
│   │   └── models.py                  # Core Pydantic v2 domain models (Task, NodeProfile, etc.)
│   ├── discovery/
│   │   └── broadcast.py               # UDP broadcast discovery on port 37020
│   ├── dlq/
│   │   └── manager.py                 # Dead-Letter Queue for exhausted tasks
│   ├── fairness/
│   │   └── drr.py                     # Deficit Round Robin (DRR) with adaptive quantum
│   ├── handlers/
│   │   ├── ai_inference.py            # Image inference handler (YOLOv8, OpenCV, PyTorch)
│   │   └── builtin.py                 # Standard handlers: log, sleep, cpu_test
│   ├── idempotency/
│   │   └── store.py                   # Deduplication store for idempotent submissions
│   ├── learning/
│   │   ├── mwu.py                     # Multiplicative Weights Update (Hedge) factor learner
│   │   └── qlearning.py               # Tabular Q-learning candidate rank selector
│   ├── node/
│   │   ├── agent.py                   # NodeAgent managing WebSocket lifecycle & execution
│   │   ├── hardware.py                # Hardware profiler (psutil, torch) & telemetry
│   │   ├── main.py                    # Node agent CLI entrypoint (taskmesh-node)
│   │   └── worker_pool.py             # WorkerPool managing concurrency, timeouts, and handlers
│   ├── orchestrator/
│   │   ├── main.py                    # Orchestrator CLI entrypoint (taskmesh-server)
│   │   ├── runtime.py                 # Central orchestrator control plane & dispatch loops
│   │   ├── server.py                  # FastAPI REST routes, WebSocket hub, and static dashboard
│   │   └── static/                    # Frontend dashboard (HTML, CSS, JS)
│   ├── persistence/
│   │   └── repositories.py            # Durable SQLite & in-memory task repositories
│   ├── protocol/
│   │   ├── messages.py                # Typed WebSocket payloads and ProtocolMessage envelope
│   │   └── version.py                 # Protocol version constant ("v1")
│   ├── queue/
│   │   └── priority.py                # Async heap-backed PriorityQueue with FIFO stability
│   ├── retry/
│   │   └── runner.py                  # Exponential backoff with random jitter & retry evaluator
│   ├── scheduler/
│   │   ├── adaptive.py                # Multi-stage AdaptiveScheduler pipeline
│   │   ├── base.py                    # Scheduler protocol & filter_eligible_nodes()
│   │   ├── baseline.py                # RoundRobin, LeastLoaded, HighestBid baselines
│   │   └── decision.py                # SchedulerDecision explainability model
│   ├── scoring/
│   │   └── base_score.py              # compute_base_score() & EWMAUpdater
│   ├── security/
│   │   └── hmac_auth.py               # SecurityManager: HMAC-SHA256, timestamp, sequence, replay
│   ├── transport/
│   │   ├── binary_protocol.py         # TMCH 48-byte header packing, parsing & SHA-256
│   │   └── payload_store.py           # BinaryPayloadStore & ChunkAssembler
│   └── wireless/
│       └── estimator.py               # NetworkEstimator: EWMA RTT & bandwidth tracking
├── tests/                             # Automated test suite (43 tests across 15 test files)
└── pyproject.toml                     # Packaging metadata, dependencies, and CLI script definitions
```

---

## 2. Recommended Reading Sequence for New Engineers

To understand TaskMesh with minimal cognitive friction, read the codebase in this order:

1. **The Domain Language**:
   [`taskmesh/core/enums.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/enums.py) $\to$ [`taskmesh/core/models.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/models.py). Understand `TaskStatus`, `Task`, `NodeProfile`, and `TaskLease`.
2. **The Protocol Contracts**:
   [`taskmesh/protocol/messages.py`](file:///C:/Malenia/TASK_MESH/taskmesh/protocol/messages.py). Review `ProtocolMessage` and the typed payloads exchanged across the network.
3. **The Control Plane Heart**:
   [`taskmesh/orchestrator/runtime.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/runtime.py). Study `_dispatch_loop`, `_health_monitor_loop`, and `handle_node_message`.
4. **The Adaptive Scheduler**:
   [`taskmesh/scheduler/adaptive.py`](file:///C:/Malenia/TASK_MESH/taskmesh/scheduler/adaptive.py). Trace the 6 stages in `select_node()` and the feedback updates in `record_task_outcome()`.
5. **The Individual Algorithmic Layers**:
   [`taskmesh/fairness/drr.py`](file:///C:/Malenia/TASK_MESH/taskmesh/fairness/drr.py) $\to$ [`taskmesh/bidding/contract_net.py`](file:///C:/Malenia/TASK_MESH/taskmesh/bidding/contract_net.py) $\to$ [`taskmesh/learning/mwu.py`](file:///C:/Malenia/TASK_MESH/taskmesh/learning/mwu.py) $\to$ [`taskmesh/learning/qlearning.py`](file:///C:/Malenia/TASK_MESH/taskmesh/learning/qlearning.py).
6. **The Compute Worker**:
   [`taskmesh/node/agent.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/agent.py) $\to$ [`taskmesh/node/worker_pool.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/worker_pool.py). See how assignments are received, executed in threads, and reported back.
7. **The Wireless & Binary Layer**:
   [`taskmesh/transport/binary_protocol.py`](file:///C:/Malenia/TASK_MESH/taskmesh/transport/binary_protocol.py) $\to$ [`taskmesh/wireless/estimator.py`](file:///C:/Malenia/TASK_MESH/taskmesh/wireless/estimator.py).

---

## 3. Module-by-Module Reference

### `taskmesh.core`
- **`enums.py`**:
  - `TaskStatus`: `PENDING`, `SCHEDULED`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRYING`, `CANCELLED`, `DLQ`. Implements `is_terminal() -> bool`.
  - `NodeStatus`: `ONLINE`, `DEGRADED`, `DRAINING`, `OFFLINE`.
  - `SchedulerMode`: `ROUND_ROBIN`, `LEAST_LOADED`, `HIGHEST_BID`, `ADAPTIVE`.
  - `OffloadPolicy`: `LOCAL_ONLY`, `WIRELESS_ALLOWED`, `REMOTE_ALLOWED`.
  - `MessageType`: All 21 typed protocol message strings.
- **`models.py`**:
  - `Task`: Stable UUID `id`, priority, status, attempt counter, active `TaskLease`, retry policy, progress, checkpoint.
  - `TaskCreate`: Input request schema for submitting work.
  - `NodeProfile`: Node specs, telemetry, `base_score`, `performance_multiplier`, `drr_deficit`, property `effective_score`.
  - `TaskLease`: Attempt-scoped lease with `expires_at` and `is_expired()`.
  - `BinaryPayloadMeta`: Enveloping payload ID, size, chunks, MIME type, and SHA-256 checksum.

### `taskmesh.orchestrator`
- **`runtime.py`**:
  - `OrchestratorRuntime`: Central coordinator.
  - Key methods:
    - `submit_task(create_req: TaskCreate, binary_data: Optional[bytes] = None) -> Task`
    - `cancel_task(task_id: str, reason: str) -> Task`
    - `retry_task(task_id: str) -> Task`
    - `drain_node(node_id: str) -> None`
    - `handle_node_message(ws, raw_data: str) -> None`
    - `create_snapshot() -> Dict[str, Any]`
    - `apply_snapshot(snapshot: Dict[str, Any]) -> None`
    - `promote_to_primary() -> None`
- **`server.py`**:
  - `create_app(runtime, config) -> FastAPI`: App factory mounting REST routes, WebSocket hub `/v1/ws/nodes`, CORS, and `/static` assets.

### `taskmesh.node`
- **`agent.py`**:
  - `NodeAgent`: WebSocket client daemon.
  - Connects to `orchestrator_url` (with fallback to `standby_url`).
  - Handles concurrent loops: `_heartbeat_loop`, `_telemetry_loop`, `_listen_loop`.
  - Reassembles binary chunks via `ChunkAssembler`.
- **`worker_pool.py`**:
  - `WorkerPool`: Thread-safe worker queue backed by `asyncio.Semaphore` and `ThreadPoolExecutor`.
  - Executes handlers with signature inspection (`checkpoint_state`, `progress_callback`, `binary_payload`).
  - Supports task cancellation via `async_task.cancel()`.
- **`hardware.py`**:
  - `profile_hardware()`: Extracts CPU cores, clock speed, RAM via `psutil`, detects CUDA GPUs via `torch`.
  - `collect_telemetry()`: Captures real-time utilization percentages.

### `taskmesh.scheduler`
- **`adaptive.py`**:
  - `AdaptiveScheduler`: Coordinates the multi-layer pipeline:
    `select_node(task, candidates) -> SchedulerDecision`
    `record_task_outcome(node, task, decision, actual_duration, success) -> None`
- **`base.py`**:
  - `filter_eligible_nodes(task: Task, nodes: List[NodeProfile]) -> List[NodeProfile]`
- **`baseline.py`**:
  - `RoundRobinScheduler`, `LeastLoadedScheduler`, `HighestBidScheduler`.
- **`decision.py`**:
  - `SchedulerDecision`: Pydantic model recording complete explainability metadata.

### `taskmesh.fairness`, `scoring`, `bidding`, `learning`
- **`taskmesh.fairness.drr.py`**:
  - `DRRFairnessManager`: Corrected deficit replenishment gating.
  - `calculate_fairness_cv(task_counts: List[int]) -> float`.
- **`taskmesh.scoring.base_score.py`**:
  - `compute_base_score(profile)`
  - `EWMAUpdater`: Speed ratio tracking and clamping.
- **`taskmesh.bidding.contract_net.py`**:
  - `calculate_node_bid(node, task, weights) -> float`.
- **`taskmesh.learning.mwu.py`**:
  - `MWUWeightLearner`: Hedge multiplicative weight updates.
- **`taskmesh.learning.qlearning.py`**:
  - `QLearningScheduler`: Tabular Q-learning with bounded state discretization and candidate rank actions.

### `taskmesh.wireless` & `transport`
- **`taskmesh.wireless.estimator.py`**:
  - `NetworkEstimator`: EWMA RTT & bandwidth tracker; compares $T_{\text{local}}$ against $T_{\text{remote}}$.
- **`taskmesh.transport.binary_protocol.py`**:
  - `create_binary_chunk_frame()`, `parse_binary_chunk_frame()`, `split_into_chunks()`, `verify_payload_checksum()`.
- **`taskmesh.transport.payload_store.py`**:
  - `BinaryPayloadStore`: 50MB bounded memory store.
  - `ChunkAssembler`: Chunk buffer with SHA-256 verification.

