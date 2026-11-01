# TaskMesh — Complete Codebase Program Inventory & Summary

This document provides a concise, program-by-program summary of every single source file, benchmark, test suite, and script in the TaskMesh repository.

---

## 1. Core Architecture & System Foundation (`taskmesh/core/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/core/enums.py`](file:///c:/Malenia/TASK_MESH/taskmesh/core/enums.py) | System enumerations | `TaskStatus`, `NodeStatus`, `SchedulerMode`, `OffloadPolicy`, `MessageType` | Defines all standard string states for task lifecycles, node health, scheduling policies, and the 21 typed WebSocket protocol message headers. |
| [`taskmesh/core/models.py`](file:///c:/Malenia/TASK_MESH/taskmesh/core/models.py) | Domain data schemas | `Task`, `TaskCreate`, `TaskLease`, `NodeProfile`, `NodeCapabilities`, `NodeTelemetry`, `TaskResult`, `BinaryPayloadMeta` | Implements Pydantic v2 data models for tasks, hardware profiles, active leases, real-time telemetry, and binary envelope metadata. |
| [`taskmesh/core/config.py`](file:///c:/Malenia/TASK_MESH/taskmesh/core/config.py) | Configuration management | `OrchestratorConfig`, `NodeConfig` | Parses environment variables and CLI parameters for ports, timeouts, lease durations, EWMA smoothing rates, and join tokens. |
| [`taskmesh/core/errors.py`](file:///c:/Malenia/TASK_MESH/taskmesh/core/errors.py) | Domain exception hierarchy | `TaskNotFoundError`, `NodeNotFoundError`, `IneligibleNodeError`, `DuplicateTaskError`, `LeaseExpiredError` | Provides custom exception types for illegal state transitions, expired leases, missing nodes, and idempotency key collisions. |

---

## 2. Control Plane & Orchestration (`taskmesh/orchestrator/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/orchestrator/runtime.py`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/runtime.py) | Central orchestration engine | `OrchestratorRuntime` | The central brain: runs background loops for task dispatching, heartbeat health checks, lease expiry revocation, and standby snapshot replication. |
| [`taskmesh/orchestrator/server.py`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py) | API server & WebSocket hub | `create_app()`, `/v1/tasks`, `/v1/ws/nodes`, `/v1/cluster/health` | FastAPI server exposing REST management endpoints, handling node WebSocket handshakes, and serving the static dashboard UI. |
| [`taskmesh/orchestrator/main.py`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/main.py) | Server CLI entrypoint | `main()` | CLI executable (`taskmesh-server` or `taskmesh server`) that parses command-line flags and boots the Uvicorn ASGI server. |
| [`taskmesh/orchestrator/static/`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/static/) | Web dashboard frontend | `index.html`, `style.css`, `app.js` | Zero-build HTML5/CSS3/JavaScript dashboard providing real-time KPI metrics, node cards, and scheduler explainability charts. |

---

## 3. Worker Node Agent & Execution Plane (`taskmesh/node/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/node/agent.py`](file:///c:/Malenia/TASK_MESH/taskmesh/node/agent.py) | Compute worker daemon | `NodeAgent` | Maintains full-duplex WebSocket connection to the orchestrator, sends periodic heartbeats/telemetry, and routes assignments to the worker pool. |
| [`taskmesh/node/worker_pool.py`](file:///c:/Malenia/TASK_MESH/taskmesh/node/worker_pool.py) | Local concurrency engine | `WorkerPool` | Controls concurrent task execution via `asyncio.Semaphore`, running CPU/GPU handlers in background thread pools without blocking async loops. |
| [`taskmesh/node/hardware.py`](file:///c:/Malenia/TASK_MESH/taskmesh/node/hardware.py) | System profiler & telemetry | `profile_hardware()`, `collect_telemetry()` | Queries physical CPU cores, RAM, and clock speeds via `psutil`, and detects dedicated NVIDIA CUDA GPUs via PyTorch. |
| [`taskmesh/node/main.py`](file:///c:/Malenia/TASK_MESH/taskmesh/node/main.py) | Node CLI entrypoint | `main()` | CLI executable (`taskmesh-node`) that parses connection URLs, worker concurrency, and capability tags, and launches `NodeAgent`. |

---

## 4. Adaptive Scheduling & Allocation Pipeline (`taskmesh/scheduler/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/scheduler/adaptive.py`](file:///c:/Malenia/TASK_MESH/taskmesh/scheduler/adaptive.py) | Central adaptive pipeline | `AdaptiveScheduler` | Pipelined scheduler: chains eligibility filtering, DRR fairness, Contract-Net bidding, MWU factor weights, Q-learning, and wireless cost checks. |
| [`taskmesh/scheduler/base.py`](file:///c:/Malenia/TASK_MESH/taskmesh/scheduler/base.py) | Scheduler protocol & filter | `Scheduler`, `filter_eligible_nodes()` | Defines abstract scheduler interface and filters out offline nodes, GPU-mismatched nodes, and memory-constrained devices. |
| [`taskmesh/scheduler/baseline.py`](file:///c:/Malenia/TASK_MESH/taskmesh/scheduler/baseline.py) | Baseline benchmark schedulers | `RoundRobinScheduler`, `LeastLoadedScheduler`, `HighestBidScheduler` | Deterministic comparative baselines used for academic benchmarking and micro-evaluations. |
| [`taskmesh/scheduler/decision.py`](file:///c:/Malenia/TASK_MESH/taskmesh/scheduler/decision.py) | Explainability audit record | `SchedulerDecision` | Pydantic schema logging the complete reasoning behind every assignment: bids, deficits, RL state-action, and wireless time breakdowns. |

---

## 5. Algorithmic Modules (`taskmesh/scoring/`, `fairness/`, `bidding/`, `learning/`, `wireless/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/scoring/base_score.py`](file:///c:/Malenia/TASK_MESH/taskmesh/scoring/base_score.py) | Capability score & EWMA | `compute_base_score()`, `EWMAUpdater` | Calculates initial hardware strength scores and updates dynamic node performance multipliers based on actual task execution speeds. |
| [`taskmesh/fairness/drr.py`](file:///c:/Malenia/TASK_MESH/taskmesh/fairness/drr.py) | Fairness controller | `DRRFairnessManager`, `calculate_fairness_cv()` | Deficit Round Robin implementation with adaptive quantum allocation and round-exhaustion gating to prevent node starvation. |
| [`taskmesh/bidding/contract_net.py`](file:///c:/Malenia/TASK_MESH/taskmesh/bidding/contract_net.py) | Auction suitability bidding | `calculate_node_bid()` | Calculates normalized suitability bids (0.0 to 1.0) combining CPU, GPU, load, latency, and historical reliability factors. |
| [`taskmesh/learning/mwu.py`](file:///c:/Malenia/TASK_MESH/taskmesh/learning/mwu.py) | Online factor weight adapter | `MWUWeightLearner` | Online Hedge learning algorithm that dynamically tunes the 5 bidding factor weights based on observed task completion losses. |
| [`taskmesh/learning/qlearning.py`](file:///c:/Malenia/TASK_MESH/taskmesh/learning/qlearning.py) | Candidate rank selector | `QLearningScheduler` | Tabular Q-learning model mapping continuous metrics into 27 discrete state buckets to choose among top-3 candidate slots with $\epsilon$-decay. |
| [`taskmesh/wireless/estimator.py`](file:///c:/Malenia/TASK_MESH/taskmesh/wireless/estimator.py) | Wireless cost model | `NetworkEstimator`, `compare_local_vs_remote()` | Tracks EWMA RTT and bandwidth to determine whether wireless image offloading is faster than local edge execution ($T_{\text{local}}$ vs. $T_{\text{remote}}$). |

---

## 6. Transport, Discovery & Security (`taskmesh/transport/`, `discovery/`, `security/`)

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/transport/binary_protocol.py`](file:///c:/Malenia/TASK_MESH/taskmesh/transport/binary_protocol.py) | Binary WebSocket chunking | `create_binary_chunk_frame()`, `parse_binary_chunk_frame()` | Packs and unpacks 64KB raw binary image frames prefixed with a 48-byte `b"TMCH"` header, bypassing Base64 overhead. |
| [`taskmesh/transport/payload_store.py`](file:///c:/Malenia/TASK_MESH/taskmesh/transport/payload_store.py) | Payload buffer & assembly | `BinaryPayloadStore`, `ChunkAssembler` | Manages 50MB in-memory payload buffers on the orchestrator and reassembles out-of-order chunks on nodes with SHA-256 verification. |
| [`taskmesh/discovery/broadcast.py`](file:///c:/Malenia/TASK_MESH/taskmesh/discovery/broadcast.py) | UDP LAN/Wi-Fi discovery | `NodeDiscoveryAdvertiser`, `DiscoveryClient` | Broadcasts and listens for UDP discovery beacons on port 37020, enabling zero-config cluster formation across local Wi-Fi. |
| [`taskmesh/security/hmac_auth.py`](file:///c:/Malenia/TASK_MESH/taskmesh/security/hmac_auth.py) | Message authentication & replay | `SecurityManager`, `compute_hmac_signature()` | Signs protocol envelopes with HMAC-SHA256, verifies 60s timestamp freshness, enforces sequence monotonicity, and caches message IDs. |
| [`taskmesh/protocol/messages.py`](file:///c:/Malenia/TASK_MESH/taskmesh/protocol/messages.py) | Wire protocol schemas | `ProtocolMessage`, `TaskAssignmentPayload`, etc. | Defines Pydantic envelopes for registrations, heartbeats, assignments, progress events, checkpoints, and completions. |
| [`taskmesh/protocol/version.py`](file:///c:/Malenia/TASK_MESH/taskmesh/protocol/version.py) | Protocol version identifier | `PROTOCOL_VERSION = "v1"` | Defines universal protocol version string to detect client/server incompatibilities. |

---

## 7. Storage, Queuing, Fault Tolerance & Handlers

| File Path | Primary Purpose | Key Classes & Functions | What It Does in 1-2 Sentences |
|---|---|---|---|
| [`taskmesh/queue/priority.py`](file:///c:/Malenia/TASK_MESH/taskmesh/queue/priority.py) | Priority heap queue | `PriorityQueue` | Asynchronous min-heap queue prioritizing high integer priorities with strict FIFO tie-breaking sequence counters. |
| [`taskmesh/persistence/repositories.py`](file:///c:/Malenia/TASK_MESH/taskmesh/persistence/repositories.py) | Durable database storage | `SQLiteTaskRepository`, `MemoryTaskRepository` | Persists task entities to a local SQLite database (`taskmesh.db`), enabling automatic state recovery across process crashes. |
| [`taskmesh/idempotency/store.py`](file:///c:/Malenia/TASK_MESH/taskmesh/idempotency/store.py) | Duplicate task deduplication | `IdempotencyStore` | In-memory key-to-task mapping that prevents duplicate executions when clients submit identical idempotency keys. |
| [`taskmesh/checkpoint/manager.py`](file:///c:/Malenia/TASK_MESH/taskmesh/checkpoint/manager.py) | Intermediate checkpoint store | `CheckpointManager` | Stores intermediate execution states per task, allowing reassigned tasks to resume from the last saved step after node failure. |
| [`taskmesh/dlq/manager.py`](file:///c:/Malenia/TASK_MESH/taskmesh/dlq/manager.py) | Dead-Letter Queue | `DLQManager`, `DLQItem` | Isolates tasks that have permanently failed after exhausting their retry budget, allowing manual inspection and recovery. |
| [`taskmesh/retry/runner.py`](file:///c:/Malenia/TASK_MESH/taskmesh/retry/runner.py) | Retry backoff calculator | `evaluate_retry()`, `compute_backoff()` | Calculates exponential backoff delays with full uniform random jitter to prevent thundering-herd retry storms. |
| [`taskmesh/cluster/registry.py`](file:///c:/Malenia/TASK_MESH/taskmesh/cluster/registry.py) | Active node tracking | `NodeRegistry` | Thread-safe mapping of live compute nodes to active WebSocket connections, managing draining states and heartbeat timestamps. |
| [`taskmesh/cluster/dev_cluster.py`](file:///c:/Malenia/TASK_MESH/taskmesh/cluster/dev_cluster.py) | Local development cluster launcher | `main()` | Spawns 1 orchestrator and $N$ independent node agent processes using `subprocess.Popen` for single-command distributed testing. |
| [`taskmesh/handlers/builtin.py`](file:///c:/Malenia/TASK_MESH/taskmesh/handlers/builtin.py) | Standard task workloads | `log_handler`, `sleep_handler`, `cpu_test_handler` | Built-in task handlers for testing logging, async sleep delays, and mathematical CPU-intensive sqrt/sin iteration loops. |
| [`taskmesh/handlers/ai_inference.py`](file:///c:/Malenia/TASK_MESH/taskmesh/handlers/ai_inference.py) | AI & vision task handlers | `image_inference_handler()` | Decodes raw binary image bytes via OpenCV and runs real YOLOv8 object detection on CUDA GPU (or PyTorch/NumPy CPU fallback). |
| [`taskmesh/cli/main.py`](file:///c:/Malenia/TASK_MESH/taskmesh/cli/main.py) | Cluster management CLI | `main()` (`taskmeshctl`) | Command-line tool for submitting tasks, uploading images, inspecting nodes, draining workers, checking health, and recovering DLQ tasks. |

---

## 8. Benchmarks & Scripts (`benchmarks/`, `scripts/`)

| File Path | Primary Purpose | What It Does in 1-2 Sentences |
|---|---|---|
| [`benchmarks/benchmark_schedulers.py`](file:///c:/Malenia/TASK_MESH/benchmarks/benchmark_schedulers.py) | Isolated scheduler microbenchmark | Measures pure decision latency and allocation fairness across Round Robin, Least Loaded, Highest Bid, and TaskMesh Adaptive for 200 tasks. |
| [`benchmarks/benchmark_distributed.py`](file:///c:/Malenia/TASK_MESH/benchmarks/benchmark_distributed.py) | Real multi-process distributed benchmark | Spawns 4 independent OS worker processes over real WebSockets and evaluates end-to-end throughput, completion time, and fairness across 3 trials. |
| [`benchmarks/benchmark_wireless.py`](file:///c:/Malenia/TASK_MESH/benchmarks/benchmark_wireless.py) | Wireless offloading benchmark | Evaluates the tipping point between local CPU execution and remote GPU Wi-Fi offload across image payload sizes from 50KB to 5MB. |
| [`benchmarks/experiment_runner.py`](file:///c:/Malenia/TASK_MESH/benchmarks/experiment_runner.py) | Benchmark execution framework | Utility library providing heterogeneous cluster topology mock fixtures, synthetic task generators, and statistical computation helpers. |
| [`benchmarks/reconcile_learning_ablations.py`](file:///c:/Malenia/TASK_MESH/benchmarks/reconcile_learning_ablations.py) | Learning ablation repeatability study | Runs 5 repeated trials to isolate and quantify the specific performance and latency contributions of Q-learning and MWU. |
| [`scripts/manual_wifi_test.py`](file:///c:/Malenia/TASK_MESH/scripts/manual_wifi_test.py) | Physical 2-machine Wi-Fi verification script | Facilitates end-to-end testing between two physical laptops on the same Wi-Fi, generating synthetic test images and tracking offload latency. |
| [`build.py`](file:///c:/Malenia/TASK_MESH/build.py) | Seminar presentation slide generator | Python script using `python-pptx` to programmatically build the 30-slide presentation deck `Adaptive_Distributed_AI_Inference_Seminar.pptx`. |

---

## 9. Automated Test Suite (`tests/`)

| File Path | Scope of Verification |
|---|---|
| [`tests/test_core_models.py`](file:///c:/Malenia/TASK_MESH/tests/test_core_models.py) | Validates task creation, attempt ID progression (`-A1`, `-A2`), and lease expiration logic. |
| [`tests/test_priority_queue.py`](file:///c:/Malenia/TASK_MESH/tests/test_priority_queue.py) | Verifies priority heap ordering and strict FIFO tie-breaking stability for equal-priority tasks. |
| [`tests/test_adaptive_pipeline.py`](file:///c:/Malenia/TASK_MESH/tests/test_adaptive_pipeline.py) | Tests the complete sequential scheduler pipeline: eligibility, scoring, DRR gating, bidding, MWU, and RL. |
| [`tests/test_rl_and_mwu_advanced.py`](file:///c:/Malenia/TASK_MESH/tests/test_rl_and_mwu_advanced.py) | Verifies Q-learning state discretization, candidate slot actions, epsilon decay, and MWU Hedge loss updates. |
| [`tests/test_ewma_adaptation.py`](file:///c:/Malenia/TASK_MESH/tests/test_ewma_adaptation.py) | Tests speed ratio calculations, multiplier clamping (0.2x to 5.0x), and recursive EWMA smoothing. |
| [`tests/test_worker_pool.py`](file:///c:/Malenia/TASK_MESH/tests/test_worker_pool.py) | Tests worker concurrency limits, asynchronous vs synchronous handlers, timeout enforcement, and cancellation. |
| [`tests/test_retry_and_dlq.py`](file:///c:/Malenia/TASK_MESH/tests/test_retry_and_dlq.py) | Verifies exponential backoff with full random jitter, retry budget exhaustion, and manual DLQ recovery. |
| [`tests/test_eligibility.py`](file:///c:/Malenia/TASK_MESH/tests/test_eligibility.py) | Tests hardware requirement filters (GPU required, RAM thresholds, capability tags) and checkpoint saving. |
| [`tests/test_security.py`](file:///c:/Malenia/TASK_MESH/tests/test_security.py) | Validates HMAC-SHA256 signatures, message tampering rejection, timestamp skew (>60s), and sequence checks. |
| [`tests/test_api_endpoints.py`](file:///c:/Malenia/TASK_MESH/tests/test_api_endpoints.py) | Tests FastAPI REST routes: submitting tasks, querying status, cancellation, draining nodes, and cluster health. |
| [`tests/test_cli.py`](file:///c:/Malenia/TASK_MESH/tests/test_cli.py) | Tests `taskmeshctl` argument parsing, sub-command routing, and REST client invocations. |
| [`tests/test_distributed_flow.py`](file:///c:/Malenia/TASK_MESH/tests/test_distributed_flow.py) | Verifies end-to-end WebSocket messaging, task dispatch, result collection, and mock node disconnect recovery. |
| [`tests/test_multi_process_distributed.py`](file:///c:/Malenia/TASK_MESH/tests/test_multi_process_distributed.py) | Launches separate OS processes via `subprocess.Popen` and validates real multi-process task dispatching over WebSockets. |
| [`tests/test_node_failure_recovery_process.py`](file:///c:/Malenia/TASK_MESH/tests/test_node_failure_recovery_process.py) | Kills a running node OS process mid-task and verifies heartbeat timeout detection, task reclamation, and reassignment. |
| [`tests/test_failover_e2e_process.py`](file:///c:/Malenia/TASK_MESH/tests/test_failover_e2e_process.py) | Kills the Primary orchestrator and verifies Standby auto-promotion and worker WebSocket re-targeting. |
| [`tests/test_persistence_restart.py`](file:///c:/Malenia/TASK_MESH/tests/test_persistence_restart.py) | Tests SQLite database crash recovery, verifying uncompleted tasks are re-enqueued on restart. |
| [`tests/test_ai_inference.py`](file:///c:/Malenia/TASK_MESH/tests/test_ai_inference.py) | Verifies YOLOv8 model loading, binary image decoding, and NumPy fallback tensor computation. |
| [`tests/test_wireless_inference.py`](file:///c:/Malenia/TASK_MESH/tests/test_wireless_inference.py) | 18-point comprehensive test suite verifying binary chunking, SHA-256 checks, 50MB limits, and wireless offload policies. |
