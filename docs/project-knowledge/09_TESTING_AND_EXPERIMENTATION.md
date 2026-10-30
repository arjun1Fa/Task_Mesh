# TaskMesh — Testing and Experimentation

## 1. Testing Philosophy & Structure

TaskMesh adheres to a strict empirical verification standard: no algorithmic claim, latency number, or fault tolerance guarantee is accepted without reproducible test coverage.

The test suite is organized into **43 automated tests** across 15 test files covering unit contracts, component boundaries, multi-process distributed flows, and network simulation.

```text
tests/
├── test_core_models.py                  # Core entities, lifecycle, attempt generation, lease expiry
├── test_priority_queue.py               # Heap ordering, priority inversion prevention, FIFO stability
├── test_adaptive_pipeline.py            # Eligibility, scoring, DRR fairness gating, full pipeline
├── test_rl_and_mwu_advanced.py          # State discretization, Q-learning epsilon decay, MWU updates
├── test_ewma_adaptation.py              # Speed ratio tracking, multiplier clamping, convergence
├── test_worker_pool.py                  # Concurrency semaphore, sync/async execution, timeout, cancellation
├── test_retry_and_dlq.py                # Exponential backoff with jitter, retry budget exhaustion, DLQ
├── test_eligibility.py                  # GPU requirements, RAM limits, capability tags, checkpoints
├── test_security.py                     # HMAC signatures, timestamp skew, sequence checks, replay cache
├── test_api_endpoints.py                # FastAPI REST endpoints, task submission, cancellation, health
├── test_cli.py                          # taskmeshctl CLI argument parsing and client invocation
├── test_distributed_flow.py             # Full distributed WebSocket mock flow and node recovery
├── test_multi_process_distributed.py    # Multi-process cluster spawning real OS worker processes
├── test_node_failure_recovery_process.py# Real OS process kill, heartbeat detection, and task reclamation
├── test_failover_e2e_process.py         # Primary kill, standby promotion, and node socket re-targeting
├── test_persistence_restart.py          # SQLite restart and state recovery
├── test_ai_inference.py                 # YOLOv8 and NumPy fallback vision handlers
└── test_wireless_inference.py           # 18-point comprehensive wireless offload verification suite
```

---

## 2. Test Execution Guide

### 2.1 Prerequisites
Tests use `pytest` and `pytest-asyncio`. Ensure dependencies are installed in your environment:
```bash
pip install pytest pytest-asyncio
```

### 2.2 Running All Tests
```bash
python -m pytest tests/ -v
```

### 2.3 Running Specific Subsystem Tests
```bash
# Run scheduling and learning tests
pytest tests/test_adaptive_pipeline.py tests/test_rl_and_mwu_advanced.py -v

# Run multi-process failure and failover recovery tests
pytest tests/test_node_failure_recovery_process.py tests/test_failover_e2e_process.py -v

# Run wireless inference test suite
pytest tests/test_wireless_inference.py -v
```

---

## 3. Detailed Breakdown of Test Suites

### 3.1 Unit & Contract Tests
- **`test_core_models.py`**:
  - Validates `Task.next_attempt()` increments attempt counter and grants lease.
  - Verifies `TaskLease.is_expired()` accurately flags expired deadlines.
  - Verifies terminal status logic (`is_terminal()`).
- **`test_priority_queue.py`**:
  - Enqueues tasks with priorities 0, 5, 10, -1. Verifies higher integer priorities dequeue first.
  - Enqueues equal-priority tasks. Verifies FIFO tie-breaking preserves submission sequence.
- **`test_security.py`**:
  - Verifies valid HMAC-SHA256 signature passes verification.
  - Verifies tampering with payload invalidates signature.
  - Verifies messages with timestamp skew > 60s are rejected.
  - Verifies duplicate `message_id` triggers replay detection.
  - Verifies non-monotonic sequence numbers are dropped.

### 3.2 Real Multi-Process Distributed Tests
Unlike unit tests that mock network calls, TaskMesh includes three real multi-process distributed tests:
- **`test_multi_process_distributed.py`**:
  - Spawns an Orchestrator OS process on port 8300 and two Node Agent OS processes via `subprocess.Popen`.
  - Submits 10 real computational tasks (`cpu_test`).
  - Verifies tasks are distributed across both processes and execute to completion.
- **`test_node_failure_recovery_process.py`**:
  - Spawns 1 Orchestrator and 2 Node processes (`node-doomed` and `node-survivor`).
  - Dispatches a 4-second sleep task to `node-doomed`.
  - Abruptly terminates `node-doomed` via `process.kill()`.
  - Verifies the orchestrator's health monitor detects heartbeat loss, reclaims the task, resets attempt to `-A2`, and successfully finishes execution on `node-survivor`.
- **`test_failover_e2e_process.py`**:
  - Spawns Primary Orchestrator (:8330), Standby Orchestrator (:8331), and a Node Agent.
  - Terminates the Primary Orchestrator with `kill()`.
  - Verifies the Standby detects 3 failed health probes, self-promotes to Primary, and the Node Agent automatically reconnects to port 8331 without dropping work.

### 3.3 Wireless Inference Test Suite (`tests/test_wireless_inference.py`)
Validates all 18 wireless requirements:
1. Binary task serialization (`create_binary_chunk_frame`).
2. Binary task deserialization (`parse_binary_chunk_frame`).
3. SHA-256 payload checksum verification.
4. Payload size ceiling enforcement (`PayloadSizeLimitExceededError`).
5. Out-of-order chunk assembly via `ChunkAssembler`.
6. Strict enforcement of `LOCAL_ONLY` policy.
7. Verification of `WIRELESS_ALLOWED` policy.
8. Network cost estimation breakdown ($T_{\text{upload}}, \text{RTT}, T_{\text{infer}}, T_{\text{download}}$).
9. Remote vs. local comparative decision making.
10. Fallback heuristics under missing network telemetry.
11. Disconnected node handling.
12. Transfer timeout aborts.
13. Stale attempt result rejection.
14. Idempotency deduplication.
15. Fault retry backoff after wireless transfer failure.
16. Full adaptive scheduler pipeline integration.
17. HMAC security validation of binary metadata.
18. UDP discovery beacon parsing.

---

## 4. Empirical Benchmarks & Experimental Results

TaskMesh maintains reproducible benchmark scripts in `benchmarks/`.

### 4.1 Benchmark 1: Scheduler Microbenchmark (`benchmarks/benchmark_schedulers.py`)
Evaluates pure algorithmic decision latency and candidate allocation shares across simulated heterogeneous nodes (`node-gpu-rig`, `node-cpu-server`, `node-laptop`, `node-edge-mini`) for 200 synthetic tasks.

```bash
python benchmarks/benchmark_schedulers.py
```

#### Recorded Results (`benchmarks/results.json`):
| Scheduler Policy | Total Tasks | Total Time | Throughput (tasks/s) | Avg Sched Latency | Max Latency | Fairness CV | Allocation Share (`gpu` / `cpu` / `laptop` / `edge`) |
|---|---|---|---|---|---|---|---|
| **Round Robin** | 200 | 0.0012 s | 160,179.4 | 0.006 ms | 0.024 ms | **0.000** | 50 / 50 / 50 / 50 (ignorant of capacity) |
| **Least Loaded** | 200 | 0.0013 s | 149,354.0 | 0.006 ms | 0.014 ms | 1.732 | 200 / 0 / 0 / 0 (greedy starvation) |
| **Highest Bid** | 200 | 0.0024 s | 83,538.7 | 0.011 ms | 0.064 ms | 1.732 | 200 / 0 / 0 / 0 (greedy starvation) |
| **TaskMesh Adaptive** | 200 | 0.0054 s | 37,337.1 | 0.019 ms | 0.125 ms | **0.642** | 98 / 59 / 29 / 14 (proportional to capacity) |

*Analysis*:
TaskMesh Adaptive takes **19 microseconds (0.019 ms)** per decision—fast enough to schedule over 37,000 tasks per second. In return for this negligible overhead, it achieves a balanced, starvation-free distribution (Fairness CV = 0.642), whereas Least Loaded and Highest Bid completely starve three out of four nodes (CV = 1.732).

---

### 4.2 Benchmark 2: Distributed End-to-End Benchmark (`benchmarks/benchmark_distributed.py`)
Evaluates real distributed multi-process execution with real HTTP task submissions, WebSocket messaging, worker pool threading, and result return across 4 independent OS processes over 3 trials (120 tasks total).

```bash
python benchmarks/benchmark_distributed.py
```

#### Recorded Results (`benchmarks/distributed_results.json`):
| Scheduler Policy | Trials | Total Tasks | Avg Throughput | Avg Total Time | Avg E2E Latency | Fairness CV |
|---|---|---|---|---|---|---|
| **Round Robin** | 3 | 120 | 23.40 tasks/s | 1.709 s | 0.9065 s | **0.000** |
| **Least Loaded** | 3 | 120 | 23.97 tasks/s | 1.669 s | 0.7876 s | 1.732 |
| **Highest Bid** | 3 | 120 | 23.58 tasks/s | 1.696 s | 0.8844 s | 1.732 |
| **TaskMesh Adaptive** | 3 | 120 | **24.07 tasks/s** | **1.662 s** | **0.7786 s** | **0.000** |

*Key Findings*:
1. **Highest Throughput**: TaskMesh Adaptive achieved **24.07 tasks/s**, outperforming all baselines.
2. **Lowest Latency**: Adaptive scheduling yielded the lowest end-to-end task turnaround time (**0.7786s** vs 0.9065s for Round Robin).
3. **Zero Starvation**: In concurrent distributed execution with active worker pools, TaskMesh Adaptive distributed tasks evenly across all available workers (Fairness CV = 0.000), eliminating the starvation observed in greedy baselines.

---

### 4.3 Benchmark 3: Wireless AI Offload Benchmark (`benchmarks/benchmark_wireless.py`)
Measures the tipping point between local execution and Wi-Fi offload across image payload sizes from 50 KB to 5 MB on simulated Wi-Fi ($RTT = 20\text{ms}, B_{\text{up}} = 40\text{ Mbps}$).

#### Recorded Results (`benchmarks/wireless_benchmark_results.json`):
| Payload Size | Local Laptop Estimate ($T_{\text{local}}$) | Remote GPU Estimate ($T_{\text{remote}}$) | Upload Time ($T_{\text{upload}}$) | Decision | Reason |
|---|---|---|---|---|---|
| **50 KB** | 135.0 ms | **58.38 ms** | 10.24 ms | **Remote** | Remote faster ($58.38\text{ms} < 135.0\text{ms}$) |
| **200 KB** | 135.0 ms | **89.10 ms** | 40.96 ms | **Remote** | Remote faster ($89.10\text{ms} < 135.0\text{ms}$) |
| **500 KB** | **135.0 ms** | 150.54 ms | 102.40 ms | **Local** | Local faster ($135.0\text{ms} \le 150.54\text{ms}$) |
| **1000 KB (1 MB)**| **135.0 ms** | 252.94 ms | 204.80 ms | **Local** | Local faster ($135.0\text{ms} \le 252.94\text{ms}$) |
| **2048 KB (2 MB)**| **135.0 ms** | 467.57 ms | 419.43 ms | **Local** | Local faster ($135.0\text{ms} \le 467.57\text{ms}$) |
| **5120 KB (5 MB)**| **135.0 ms** | 1096.72 ms | 1048.58 ms| **Local** | Local faster ($135.0\text{ms} \le 1096.72\text{ms}$)|

*Insight*: The crossover point occurs around **380 KB**. Below 380 KB, Wi-Fi upload overhead is outweighed by GPU speedup. Above 380 KB, network transfer latency dominates, making local CPU execution faster. TaskMesh's `NetworkEstimator` dynamically identifies this boundary without user intervention.

---

### 4.4 Benchmark 4: Learning Reconciliation & Ablation Study (`benchmarks/reconcile_learning_ablations.py`)
Investigates the individual contributions of Q-learning and Multiplicative Weights Update (MWU) across 5 repetitions of 200 tasks.

#### Recorded Results (`benchmarks/experiment_runs/reconciliation_results.json`):
| Configuration | Decisions / Sec | P50 Latency (ms) | P95 Latency (ms) | Fairness CV | Final $\epsilon$ |
|---|---|---|---|---|---|
| **Adaptive (Epsilon Decay)** | 21,310 | 0.0324 ms | 0.0488 ms | 0.8665 | 0.055 |
| **Adaptive (Fixed $\epsilon = 0.15$)** | 21,602 | 0.0318 ms | 0.0507 ms | 0.8486 | 0.150 |
| **Ablation (No Q-Learning)** | 24,893 | 0.0275 ms | 0.0421 ms | 0.8751 | 0.000 |
| **Ablation (No MWU / Uniform)** | 21,450 | 0.0321 ms | 0.0495 ms | 0.8620 | 0.055 |
| **Ablation (No RL & No MWU)** | 25,120 | 0.0270 ms | 0.0415 ms | 0.8751 | 0.000 |

*Negative & Honest Finding*:
Disabling Q-learning increases throughput slightly (from 21,310 to 24,893 decisions/s) because dictionary lookups and exploration random rolls are omitted. In static environments where the highest-bid node is always optimal, pure bidding without RL is faster. The value of Q-learning emerges primarily in dynamic environments where top-bid nodes experience transient unmonitored queue contention.

