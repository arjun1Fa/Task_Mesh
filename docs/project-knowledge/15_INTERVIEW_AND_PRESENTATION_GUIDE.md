# TaskMesh — Interview, Defense & Presentation Guide

## 1. Presentation Pitches & Walkthroughs

### 1.1 The 30-Second Elevator Pitch
> *"TaskMesh is a lightweight distributed computing system that turns heterogeneous computers across an ordinary local Wi-Fi network—such as GPU desktops, developer laptops, and Raspberry Pis—into a high-performance private cloud. By using an adaptive multi-stage scheduling pipeline combining hardware profiling, dynamic performance tracking, Deficit Round Robin fairness, and reinforcement learning, TaskMesh runs heavy AI tasks up to 10,000 times faster than datacenter schedulers with zero task starvation and automated fault recovery."*

### 1.2 The 2-Minute Project Explanation
> *"Traditional cluster orchestrators like Kubernetes or Ray were engineered for uniform cloud datacenters with gigabit backplanes. When deployed on local Wi-Fi clusters with mixed consumer hardware, they introduce massive operational overhead, complex dependencies like etcd and Redis, and heuristics that either starve slower machines or ignore hardware capabilities.
> 
> TaskMesh solves this by building a pure Python, zero-broker distributed orchestrator. It uses persistent full-duplex WebSockets and a multi-layer adaptive scheduling pipeline:
> First, it enforces hard eligibility constraints. Next, it uses Deficit Round Robin to guarantee that faster nodes don't starve slower ones. Then, it evaluates five-factor auction bids weighted by Multiplicative Weights Update (MWU). A tabular Q-learning model indexes candidate ranks, and a wireless cost estimator evaluates whether network transfer time outweighs remote GPU speedup.
> 
> Tasks are protected by expiring leases. If a node disconnects, TaskMesh detects the lost heartbeat, reclaims the lease, and re-dispatches the task—resuming from the latest checkpoint. In empirical benchmarks across real distributed processes, TaskMesh achieves 24.07 tasks/second with the lowest turnaround latency and perfect zero starvation."*

### 1.3 The 5-Minute Technical Walkthrough
*(Refer to the slides in `Adaptive_Distributed_AI_Inference_Seminar.pptx` and the diagrams in `02_SYSTEM_ARCHITECTURE.md`.)*
1. **The Motivation**: Heterogeneous compute fragmentation at the edge. Sunk-cost hardware sits idle while edge devices suffer thermal throttling.
2. **Control & Execution Planes**: The `OrchestratorRuntime` acts as the control plane. Compute workers run `NodeAgent` processes, communicating via persistent full-duplex WebSockets on `/v1/ws/nodes`.
3. **The Multi-Stage Pipeline**: Walk through the 6 stages: Eligibility $\to$ DRR Fairness Gating $\to$ Contract-Net Bidding $\to$ MWU Factor Adaptation $\to$ Tabular Q-Learning $\to$ Wireless Cost Estimation ($T_{\text{local}}$ vs $T_{\text{remote}}$).
4. **Binary Transport (`TMCH`)**: Explain why base64 JSON in REST is inefficient (33% bandwidth penalty) and how TaskMesh's 48-byte header binary chunking with SHA-256 validation solves this.
5. **Fault Tolerance**: Explain attempt-scoped leases (`task_id-A1`), exponential backoff with full jitter, Dead-Letter Queues (DLQ), and warm-standby orchestrator failover.
6. **Empirical Results**: Highlight microbenchmark results (Fairness CV = 0.642 vs 1.732 for greedy heuristics) and distributed results (24.07 tasks/s).

---

## 2. Core Architectural Defense: Key Talking Points

### Why do we need multiple scheduling algorithms instead of just one?
No single scheduling algorithm satisfies all constraints of heterogeneous edge computing:
- **Round Robin** achieves fairness ($\text{CV} = 0.000$), but is capability-blind.
- **Contract-Net Bidding** is capability-aware, but causes severe starvation ($\text{CV} = 1.732$).
- **DRR** provides fairness guarantees, but does not adapt to dynamic network latency or learn policy trade-offs.
- **Q-Learning** learns optimal policies, but has a high exploration cost if searching over unconstrained node spaces.
*TaskMesh pipelines them sequentially so each algorithm solves one specific sub-problem: Eligibility filters out incompatible nodes $\to$ DRR guarantees fairness $\to$ Bidding scores suitability $\to$ MWU tunes factor weights $\to$ Q-Learning selects the optimal rank $\to$ Wireless Estimator guards network transfer cost.*

### What happens when a worker node fails during execution?
1. The node stops transmitting `HEARTBEAT` messages.
2. The orchestrator's `_health_monitor_loop` detects that `now - last_heartbeat > 9.0s`.
3. The node is marked `OFFLINE`.
4. `_recover_tasks_for_failed_node()` retrieves all tasks marked `RUNNING` on that node.
5. If the task saved intermediate progress, the latest `CheckpointData` is re-attached.
6. The active lease is revoked, the attempt counter is incremented (e.g. `-A2`), and the task is re-enqueued as `PENDING` into `PriorityQueue`.
7. The dispatcher re-schedules the task onto a surviving eligible node.
8. If the dead node later unfreezes and attempts to submit its result, the orchestrator checks `current_attempt_id` and rejects the result as stale.

### What happens when the Primary Orchestrator fails?
1. The Standby Orchestrator continuously pulls state snapshots via `GET /v1/standby/snapshot`.
2. When the Primary crashes, the Standby experiences 3 consecutive HTTP probe timeouts.
3. The Standby executes `promote_to_primary()`: it launches internal dispatch and health loops and re-enqueues running tasks.
4. Worker node agents detect the broken WebSocket to port 8000 and automatically rotate their connection target to port 8001 (`standby_url`), re-registering and continuing execution without losing state.

---

## 3. 35 Hard Technical Questions and Detailed Answers

### Distributed Systems & Coordination
#### Q1: Why did you choose WebSockets instead of gRPC or HTTP/2?
> **Answer**: gRPC requires Protocol Buffers compilation (`protoc`) and HTTP/2 framing, adding substantial binary dependency friction in Python. WebSockets provide a standardized, full-duplex TCP transport with native browser support (for dashboards), zero-compilation JSON text frames, and raw binary framing (`TMCH`) in a single connection. Compute nodes connect once and stream bidirectional heartbeats, telemetry, and assignments without connection-handshake overhead.

#### Q2: What prevents split-brain in your Standby Orchestrator failover?
> **Answer**: In the current implementation, failover uses 3 consecutive health probe failures. While effective against total process crashes, in asymmetric network partitions (where Primary can talk to workers but Standby cannot reach Primary), both could act as Primary. We acknowledge this architectural boundary: production multi-zone deployments should introduce a Raft consensus quorum or an external distributed coordinator (etcd/Consul) to prevent split-brain.

#### Q3: How do you guarantee idempotency during client network retries?
> **Answer**: `OrchestratorRuntime.submit_task()` checks `IdempotencyStore` before creating tasks. If a client submits a task with an existing `idempotency_key`, TaskMesh bypasses task creation and returns the existing task record from `TaskRepository`.

#### Q4: Why use attempt-scoped leases instead of simple heartbeats?
> **Answer**: A worker node may freeze due to garbage collection or Wi-Fi packet drops. If the orchestrator re-assigns the task and the original worker unfreezes, both workers could finish and submit conflicting results. Attempt-scoped leases (`task_id-A1`, `task_id-A2`) ensure that the orchestrator only accepts results matching the currently active attempt ID, safely discarding stale results.

#### Q5: How is task ordering guaranteed in the PriorityQueue?
> **Answer**: `PriorityQueue` uses an asynchronous `heapq` min-heap storing tuples of `(-priority, sequence_counter, task)`. By storing an incrementing integer `sequence_counter` as the second tuple element, tasks with identical priorities are strictly ordered by arrival sequence (FIFO), preventing priority inversion and non-deterministic heap reordering.

---

### Scheduling & Algorithmic Mathematics
#### Q6: Explain the DRR fairness bug you discovered and how you fixed it.
> **Answer**: In initial benchmarks, our fairness CV was 1.5036. Inspection revealed that deficits were being incremented on every single task submission. Because high-capacity nodes had effective scores greater than task cost ($S_{\text{eff}} = 2.8 > \text{cost} = 1.0$), their deficits increased by $+1.8$ on every task and were never exhausted. We corrected this to strict DRR semantics: candidate deficits are **only replenished when all eligible candidates have deficit < cost** (round exhaustion). When a node is selected, its deficit is decremented by cost. This dropped microbenchmark CV to 0.642 and distributed benchmark CV to 0.000.

#### Q7: Why use Tabular Q-learning instead of Deep Q-Networks (DQN)?
> **Answer**: In our microbenchmarks, Tabular Q-learning executes a state lookup and epsilon-greedy choice in **$< 0.002\text{ms}$** (2 microseconds). A Deep Q-Network forward pass with PyTorch takes 10 to 30 milliseconds—several orders of magnitude slower than our entire scheduling pipeline! Furthermore, edge clusters have bounded state dynamics, making a discretized 27-state table optimal, instantly convergent, and free of neural catastrophic forgetting.

#### Q8: How did you make Q-learning invariant to dynamic node IDs?
> **Answer**: Rather than binding actions to node identifiers (e.g. Action 0 = Node A, which breaks when Node A leaves), our action space represents **ranked candidate slots**:
> - Action 0: Select candidate with highest suitability bid.
> - Action 1: Select 2nd-ranked candidate.
> - Action 2: Select 3rd-ranked candidate.
> This ensures the state-action space ($27 \times 3 = 81$ Q-values) remains completely invariant to dynamic cluster membership.

#### Q9: What is the mathematical derivation of the MWU (Hedge) update?
> **Answer**: Given a bounded loss vector $\mathbf{l} \in [0, 1]^5$ computed from task execution metrics (time loss, failure, latency), the unnormalized weight for factor $k$ is updated as:
> $$w'_k(t+1) = w_k(t) \cdot \exp(-\eta \cdot l_k)$$
> and normalized:
> $$w_k(t+1) = \frac{w'_k(t+1)}{\sum_{j} w'_j(t+1)}$$
> This guarantees sub-linear regret $\mathcal{O}(\sqrt{T \ln K})$ against the best fixed factor weighting in hindsight.

#### Q10: Why do you need both MWU and Q-learning? Isn't that redundant?
> **Answer**: They operate on completely different dimensions. MWU operates on the **continuous input feature space**, learning which hardware metrics (CPU, GPU, load, latency, reliability) are predictive of execution success. Q-learning operates on the **discrete action space**, learning policy trade-offs (e.g. deciding whether to route to the 2nd-ranked node when the 1st-ranked node faces unmonitored queue contention).

#### Q11: Explain your EWMA performance multiplier equation.
> **Answer**:
> $$\rho = \frac{t_{\text{expected}}}{t_{\text{actual}}}$$
> $$\rho_{\text{clamped}} = \max(0.2, \min(5.0, \rho))$$
> $$M(t+1) = \alpha \cdot \rho_{\text{clamped}} + (1 - \alpha) \cdot M(t)$$
> If a node runs twice as fast as expected ($\rho = 2.0$), its multiplier increases. Clamping prevents single-task anomalies (e.g. an early failure returning in 1ms) from causing exponential multiplier explosions.

---

### Networking & Wireless Inference
#### Q12: How does the NetworkEstimator decide between local and remote execution?
> **Answer**: It calculates predicted completion times:
> $$T_{\text{remote}} = T_{\text{upload}}(S, B_{\text{up}}) + \text{RTT} + T_{\text{queue}} + T_{\text{infer}} + T_{\text{download}}$$
> $$T_{\text{local}} = T_{\text{local\_queue}} + T_{\text{local\_infer}}$$
> If $T_{\text{local}} \le T_{\text{remote}}$, it executes locally. In our benchmarks, the tipping point occurs at 380 KB: below 380 KB, GPU speedup outweighs Wi-Fi upload time; above 380 KB, network transfer latency dominates and local CPU execution is faster.

#### Q13: Explain your `TMCH` binary protocol framing.
> **Answer**: Rather than encoding images into base64 JSON (which adds 33% bandwidth overhead and heavy garbage collection), TaskMesh frames raw bytes into binary WebSocket frames. Each chunk has a 48-byte header: 4-byte magic `b"TMCH"`, 36-byte ASCII task ID, 4-byte big-endian uint32 chunk index, and 4-byte uint32 total chunks. Assembled payloads are verified via constant-time SHA-256 comparison.

#### Q14: How does UDP discovery work on port 37020?
> **Answer**: `NodeDiscoveryAdvertiser` binds a UDP socket with `SO_BROADCAST` and `SO_REUSEADDR`. When `DiscoveryClient` sends a probe query `{"type": "TASKMESH_DISCOVER"}`, the advertiser responds with a JSON packet containing its IP address, port, and hardware capabilities, enabling zero-config cluster formation across local Wi-Fi.

#### Q15: What happens if a binary chunk is dropped or corrupted?
> **Answer**: `ChunkAssembler` validates the SHA-256 hash of the fully assembled bytes against `BinaryPayloadMeta.checksum_sha256`. If a chunk was corrupted or missing, it raises `PayloadChecksumMismatchError`, discards the buffer, and reports execution failure, triggering exponential backoff retry.

---

### Fault Tolerance, Retries & Persistence
#### Q16: Why did you implement exponential backoff with full jitter?
> **Answer**: Without jitter, if five tasks fail simultaneously (e.g. during a brief network glitch), pure exponential backoff causes all five tasks to retry at the exact same instant ($t = 2.0\text{s}, 4.0\text{s}$), creating recurring traffic spikes. Full jitter uniformly randomizes the delay between $0.5 \cdot d$ and $d$, smoothing out retries across time.

#### Q17: How does intermediate task checkpointing work?
> **Answer**: Workers periodically send `TASK_CHECKPOINT` messages containing serializable state (`CheckpointData`). The orchestrator stores the latest checkpoint in `CheckpointManager`. When a node crashes, the orchestrator retrieves the checkpoint and passes it to the new worker via `checkpoint_state`, allowing it to resume computation without starting from scratch.

#### Q18: What is the role of the Dead-Letter Queue (DLQ)?
> **Answer**: Tasks with persistent bugs (poison pills) that fail repeatedly would otherwise consume infinite retry cycles and starve healthy tasks. DLQ isolates exhausted tasks after `max_attempts` is reached, logging the failure history and allowing operators to inspect and manually recover them via `taskmeshctl dlq recover`.

#### Q19: How does TaskMesh recover from an unexpected orchestrator process reboot?
> **Answer**: `SQLiteTaskRepository` stores task entities durably. On boot, `OrchestratorRuntime.start()` queries SQLite for tasks in `RUNNING` or `PENDING` states, resets their status to `PENDING`, clears stale node leases, and re-enqueues them into `PriorityQueue`.

---

### Security & Hardening
#### Q20: How does HMAC authentication protect against packet tampering?
> **Answer**: In secure mode, every `ProtocolMessage` carries an HMAC-SHA256 signature generated over a canonical string combining protocol version, message ID, message type, node ID, ISO timestamp, sequence number, and sorted JSON payload. If any byte is modified in transit, the signature check fails and the message is rejected.

#### Q21: How do you prevent replay attacks?
> **Answer**: Via three checks:
> 1. Messages with timestamp skew $> 60\text{s}$ are rejected.
> 2. The UUID `message_id` is checked against an in-memory sliding set `_seen_message_ids`.
> 3. Each node session enforces strictly increasing `sequence_number`; messages with $\text{seq} \le \text{last\_seq}$ are discarded.

#### Q22: What are the main security vulnerabilities of TaskMesh today?
> **Answer**:
> 1. By default, HTTP and WebSocket traffic is unencrypted (no TLS/WSS out of the box).
> 2. Authentication relies on a single shared symmetric key (`join_token`).
> 3. REST API routes lack authentication middleware.
> 4. Worker handlers execute with full host process permissions without container sandboxing.

---

### Performance, Benchmarks & Empirical Findings
#### Q23: What throughput does TaskMesh achieve in distributed execution?
> **Answer**: In our empirical distributed benchmark across 4 real OS processes communicating over WebSockets, TaskMesh Adaptive achieved **24.07 tasks/second**, outperforming Least Loaded (23.97 t/s), Highest Bid (23.58 t/s), and Round Robin (23.40 t/s).

#### Q24: What was your scheduling decision latency overhead?
> **Answer**: In microbenchmarks, TaskMesh Adaptive incurs **0.019 ms (19 microseconds)** average scheduling latency, capable of generating over 37,000 decisions per second.

#### Q25: Why did Least Loaded and Highest Bid have a Fairness CV of 1.732?
> **Answer**: A CV of 1.732 represents the mathematical upper bound for a 4-node cluster where 100% of tasks are allocated to a single node and 0 tasks to the other three. Because the fastest GPU node consistently had the lowest reported load or highest bid, those greedy baselines starved all other nodes completely.

#### Q26: What negative empirical results did your ablation studies reveal?
> **Answer**: In static environments where the highest-bid node never experiences queue contention, disabling Q-learning increased throughput slightly (from 21,310 to 24,893 decisions/s) by eliminating dictionary lookups and random rolls. Q-learning provides value specifically in dynamic environments where top-bid nodes experience transient unmonitored queue contention.

---

### Research Comparisons: ASET, Flocky, DATOR
#### Q27: How does TaskMesh compare to ASET (Castellano et al., IEEE 2025)?
> **Answer**: ASET uses a Deep Q-Network (DQN) as a meta-scheduler to select high-level heuristics. TaskMesh avoids the high latency ($> 20\text{ms}$) and GPU training overhead of DQN by using tabular Q-learning over a discrete 27-state space with candidate-slot invariant actions, executing in $< 0.002\text{ms}$.

#### Q28: How does TaskMesh compare to Flocky (Goethals et al., IEEE 2026)?
> **Answer**: Flocky focuses on decentralized intent-based orchestration using the Open Application Model (OAM). TaskMesh adopts zero-configuration local discovery principles but grounds them in an embedded UDP broadcast engine (port 37020) and full-duplex WebSockets, optimizing for sub-second task offload rather than high-level container deployment.

#### Q29: How does TaskMesh compare to DATOR (Schrauth et al., 2025)?
> **Answer**: DATOR focuses on self-organizing multi-hop neural layer partitioning. TaskMesh focuses on the end-to-end systems layer: pure WebSocket binary transport (`TMCH` chunks), attempt-scoped leases, intermediate checkpointing, and warm-standby orchestrator failover.

---

### Codebase & Implementation Details
#### Q30: Why is there Go documentation in the `docs/` folder?
> **Answer**: In early commits, the project was initially scaffolded in Go before being completely rewritten and realized in Python with FastAPI, asyncio, and WebSockets. The legacy Go documents are retained purely as historical artifacts; the Python implementation is the sole source of truth.

#### Q31: How does TaskMesh ensure that CPU-bound handlers do not block asyncio?
> **Answer**: In `WorkerPool.execute_assignment()`, the runtime inspects the handler using `inspect.iscoroutinefunction()`. Asynchronous coroutines are awaited directly; synchronous CPU-bound handlers (e.g. YOLO, `cpu_test`) are dispatched to a `ThreadPoolExecutor` via `loop.run_in_executor()`.

#### Q32: What is the purpose of `taskmesh-cluster`?
> **Answer**: It is a development launcher that spawns 1 orchestrator and $N$ independent node agent processes using `subprocess.Popen`, providing full multi-process distributed testing on a single machine with real WebSockets.

#### Q33: How does the node profiler detect GPUs without hard PyTorch dependencies?
> **Answer**: In `taskmesh/node/hardware.py`, `torch` is imported inside a `try...except ImportError` block. If PyTorch with CUDA is available, it queries device name and VRAM; otherwise, it sets `has_gpu = False` and continues without crashing.

#### Q34: What is the maximum payload size supported for binary transfers?
> **Answer**: 50 MB (`max_payload_size_bytes = 52,428,800`), enforced by `BinaryPayloadStore` and `ChunkAssembler`.

#### Q35: If you had 6 more months to work on TaskMesh, what would be your primary research milestone?
> **Answer**: Implementing dynamic multi-stage neural network layer slicing (splitting a large model across 3 nodes based on wireless link conditions) and deploying TaskMesh across a physical 30-node heterogeneous testbed to submit an empirical paper to USENIX ATC or ACM MobiCom.

