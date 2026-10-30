# TaskMesh — Glossary of Terms & Concepts

## A
- **Adaptive Scheduling**: The dynamic, multi-stage scheduling technique in TaskMesh that evaluates hardware capability, dynamic performance multipliers, fairness deficits, auction bids, online weight adaptations, reinforcement learning slot choices, and wireless network transfer costs to select an execution node.
- **ASET**: Adaptive Scheduling for Edge Tasks (Castellano et al., IEEE ICDCSW 2025). A research paper proposing Deep Q-Networks (DQN) as a meta-scheduler for inference workloads. TaskMesh optimizes this concept by replacing heavyweight DQN forward passes with sub-millisecond tabular Q-learning.
- **ASGI**: Asynchronous Server Gateway Interface. The standard Python interface between async-capable web servers (Uvicorn) and web frameworks/applications (FastAPI).
- **Attempt ID**: A unique, attempt-scoped string identifier (e.g. `task_12345-A1`, `task_12345-A2`) assigned to each discrete execution attempt of a task. Used to detect and reject stale results from delayed or unfreezing workers.

## B
- **Base Score ($S_{\text{base}}$)**: A static, normalized representation of a compute node's raw hardware strength calculated upon registration from CPU cores, clock speed, RAM, and GPU presence.
- **Bellman Equation**: The fundamental recursive optimality equation in reinforcement learning used by `QLearningScheduler` to update state-action Q-values upon observing task execution rewards.
- **Binary Payload Store (`BinaryPayloadStore`)**: The thread-safe in-memory cache on the orchestrator that holds unchunked binary images or tensors (up to 50MB) and pre-computes SHA-256 digests.

## C
- **Checkpoint Data (`CheckpointData`)**: Intermediate execution progress and state saved by a worker and streamed to the orchestrator. Enables another node to resume execution mid-way if the original worker crashes.
- **Chunk Assembler (`ChunkAssembler`)**: The reassembly engine running on node agents that collects out-of-order 64KB binary WebSocket frames, verifies chunk counts, re-assembles the complete payload, and verifies the SHA-256 hash.
- **Coefficient of Variation (CV)**: The ratio of standard deviation to mean ($\sigma / \mu$) used to measure allocation fairness. $\text{CV} = 0.0$ indicates perfect uniform task distribution; high CV indicates severe node starvation.
- **Contract Net Protocol (CNP)**: A multi-agent negotiation framework where an orchestrator announces tasks and worker nodes submit suitability bids. TaskMesh adapts this into a 5-factor normalized auction score.

## D
- **DATOR**: Dynamic, Adaptive, and Topology-Optimized Routing (Schrauth et al., Applied Sciences 2025). A research paper investigating self-organized distributed inference and resilience without central control.
- **Dead-Letter Queue (DLQ)**: An isolated storage queue for poison-pill tasks that have exhausted their retry budget (`retry_count >= max_attempts`), preventing infinite retry loops.
- **Deficit Round Robin (DRR)**: A fair-queuing algorithm with adaptive quantum accumulation that guarantees proportional task allocation across heterogeneous nodes, preventing greedy starvation of slower devices.
- **Draining Mode (`NodeStatus.DRAINING`)**: An administrative state where a node rejects all new task offers, completes its currently active in-flight tasks, and disconnects cleanly.

## E
- **Effective Score ($S_{\text{eff}}$)**: The dynamic computational score of a node, defined as $S_{\text{eff}} = \max(0.01, S_{\text{base}} \cdot M)$, where $M$ is the dynamic EWMA performance multiplier.
- **Exponentially Weighted Moving Average (EWMA)**: A recursive moving average applying exponentially decaying weighting factors ($\alpha$), used in TaskMesh to smooth execution speed ratios, network RTT, and Wi-Fi bandwidth.

## F
- **FastAPI**: Modern, high-performance web framework for Python used by TaskMesh to expose REST management routes, OpenAPI documentation, and WebSocket endpoints.
- **Flocky**: Decentralized Intent-based Edge Orchestration (Goethals et al., IEEE TSC 2026). A research paper investigating intent-based edge scheduling and zero-dependency local discovery using the Open Application Model (OAM).

## H
- **Hardware Profiler (`profile_hardware`)**: The inspection subsystem on node agents using `psutil` and `torch` to dynamically extract CPU core counts, frequency, physical RAM, and GPU VRAM.
- **Hedge Algorithm**: The multiplicative weight update algorithm used by `MWUWeightLearner` to adapt bidding factor weights based on bounded execution loss vectors.
- **HMAC-SHA256**: Keyed-Hash Message Authentication Code using SHA-256. Cryptographic message integrity mechanism securing WebSocket protocol frames in TaskMesh secure mode.

## I
- **Idempotency Key**: A unique client-supplied token that ensures submitting the exact same task multiple times produces only a single execution, returning the existing task entity.

## L
- **Lease (`TaskLease`)**: A time-bounded grant of execution rights issued by the orchestrator to a specific node for a specific attempt. If the lease expires without progress, the orchestrator revokes ownership.

## M
- **Multiplicative Weights Update (MWU)**: An online learning algorithm that updates a probability distribution over decision factors (CPU, GPU, load, latency, reliability) based on observed task outcome losses.

## N
- **Network Estimator (`NetworkEstimator`)**: The wireless telemetry component tracking RTT and upload/download speeds to compare predicted local execution time against remote wireless offload time.
- **Node Agent (`NodeAgent`)**: The background daemon running on worker machines that maintains persistent WebSocket connectivity with the orchestrator, profiles hardware, and executes tasks.

## O
- **Offload Policy (`OffloadPolicy`)**: Privacy and network constraints governing task execution: `LOCAL_ONLY` (must run on originating node), `WIRELESS_ALLOWED` (offload if predicted faster), or `REMOTE_ALLOWED`.
- **Orchestrator Runtime (`OrchestratorRuntime`)**: The central control plane engine managing task persistence, priority queueing, dispatch loops, health monitors, and high-availability failover.

## P
- **Priority Queue (`PriorityQueue`)**: An asynchronous heap queue storing pending tasks ordered by priority integer, with FIFO sequence numbers breaking ties.
- **Protocol Message (`ProtocolMessage`)**: The universal typed JSON envelope carrying all control events, sequence numbers, timestamps, and HMAC signatures.

## Q
- **Q-Learning Scheduler (`QLearningScheduler`)**: A reinforcement learning model using candidate-slot actions (Slot 0, 1, 2) and discretized state tuples to select among top-ranked candidate nodes.

## R
- **Round Replenishment**: The critical event in Deficit Round Robin when all eligible candidates have deficit $< \text{cost}$, triggering an addition of adaptive quantum $Q_n$ to all candidates.

## S
- **Standby Mode (`standby_mode`)**: An operational mode where a secondary orchestrator continuously polls state snapshots from the primary, ready to promote itself upon primary failure.

## T
- **`TMCH` Framing**: The 48-byte fixed binary header (`b"TMCH"`) prepended to raw WebSocket binary frames for transmitting large images in 64KB chunks without base64 overhead.

## U
- **UDP Broadcast Discovery (`NodeDiscoveryAdvertiser` / `DiscoveryClient`)**: The zero-dependency LAN discovery mechanism operating on UDP port `37020` that enables nodes to find orchestrators on local Wi-Fi.

## W
- **Worker Pool (`WorkerPool`)**: The local execution subsystem on node agents managing concurrency semaphores, asyncio coroutines, and thread pool executor offloading.

