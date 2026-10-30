# TaskMesh — Problem Statement and Motivation

## 1. Introduction & Context

In modern computational environments, compute capacity is fragmented across a vast array of consumer and edge hardware. In university research laboratories, small tech enterprises, smart buildings, robotics environments, and remote field deployments, there exists an abundance of heterogeneous hardware:
- Dedicated desktop workstations equipped with consumer-grade CUDA GPUs (e.g., NVIDIA GeForce RTX 3080/4090).
- Multi-core developer laptops (Intel Core, AMD Ryzen, Apple Silicon).
- Lightweight edge computers and IoT hubs (Raspberry Pi 4/5, Intel NUCs, NVIDIA Jetson modules).

In typical everyday operations, **these machines sit idle for greater than 70% of the working day**. Meanwhile, when researchers, developers, or sensor pipelines (e.g., high-framerate surveillance cameras, autonomous ground vehicles) need to execute computationally intensive AI inference tasks (such as YOLOv8 object detection, image segmentation, or embedding generation), they face severe operational bottlenecks:
1. **Local Device Overload**: Battery-powered or low-spec edge devices take hundreds of milliseconds or seconds to process a single frame, inducing thermal throttling and depleting batteries.
2. **Cloud Dependency Pitfalls**: Offloading to public cloud hyperscalers (AWS, Google Cloud, Azure) incurs continuous egress fees, unpredictable wide-area network (WAN) latencies, Internet uplink jitter, and grave privacy/regulatory violations (e.g., transmitting sensitive video streams over public networks).
3. **Infrastructure Complexity of Datacenter Frameworks**: Existing cluster orchestrators (Kubernetes/K8s, Ray, Apache Spark, Celery) were engineered for homogenous cloud datacenters with gigabit backplanes and persistent public IPs. Deploying them on an ad-hoc local Wi-Fi / LAN network requires substantial infrastructure (DNS servers, container registries, message brokers like RabbitMQ or Redis, distributed key-value stores like etcd), consuming excessive memory and requiring specialized DevOps maintenance.

**TaskMesh exists to bridge this fundamental gap.**

---

## 2. Why Heterogeneous Hardware Pooling Instead of One Single Machine?

A common counter-argument is: *"Why not simply purchase one large, monolithic GPU server and run everything on it?"*

While a single monolithic server is attractive in a managed datacenter, in distributed edge environments, real-world constraints dictate otherwise:

1. **Physical Proximity & Network Locality**: In many distributed domains (smart factories, robotic swarms, multi-room building monitoring), compute nodes are physically distributed across multiple rooms, floors, or outdoor zones. Transmitting continuous raw 4K video feeds or sensor data over Wi-Fi back to a single central machine rapidly saturates the wireless access point's radio spectrum. Distributed local processing near the source prevents LAN choke points.
2. **Economic Sunk-Cost Efficiency**: Organizations have already purchased laptops, workstations, and edge computers for individual staff. Pooling these pre-existing, already-purchased machines provides aggregated compute power for zero incremental hardware cost.
3. **Graceful Degradation vs. Single Point of Failure**: If a single centralized server crashes, power-cycles, or suffers hardware failure, the entire organization or sensor network halts immediately. In a heterogeneous mesh, the loss of one machine simply causes TaskMesh to dynamically adapt, re-route tasks, and continue running on the remaining nodes.
4. **Thermal and Power Constraints**: Distributing compute workloads across multiple edge nodes spreads heat dissipation and electrical draw across different circuits and batteries, preventing localized overheating in enclosed edge deployments.

---

## 3. What Makes TaskMesh Different from Conventional Distributed Systems?

| Dimension | Datacenter Systems (Kubernetes, Ray, Spark) | Message Brokers (Celery, RabbitMQ) | TaskMesh |
|---|---|---|---|
| **Primary Target** | Homogeneous datacenter VMs / Bare-metal racks | Backend task workers with shared DB | Heterogeneous consumer & edge machines across local Wi-Fi/LAN |
| **Network Assumption** | Ultra-fast, low-jitter gigabit backplane | Stable internal private subnet | Volatile LAN / Wi-Fi with fluctuating RTT and packet loss |
| **Dependencies** | Docker/containerd, etcd, ZooKeeper, heavy daemons | Redis, RabbitMQ, PostgreSQL/MySQL | Zero external brokers; pure Python runtime with WebSocket transport |
| **Hardware Awareness** | Coarse static tags (`gpu=true`, `cpu=4`) | No hardware awareness (blind queue consumption) | Deep dynamic profiling (CPU, RAM, GPU, EWMA execution speed) |
| **Scheduling Decision** | Bin-packing, FIFO, or static round-robin | Worker-pull FIFO queue (greedy worker consumption) | Multi-stage adaptive pipeline: Eligibility → DRR → Bidding → MWU → RL → Wireless Cost |
| **Wireless AI Offload** | Absent (assumes infinite bandwidth) | Absent | First-class cost estimator ($T_{\text{local}}$ vs. $T_{\text{remote}}$) & binary chunking (`TMCH`) |
| **Resource Overhead** | Gigabytes of RAM for control plane | Moderate memory footprint for brokers | Extremely lightweight (< 50MB RAM for control plane) |

---

## 4. Formal Problem Statement

Let a local cluster consist of a set of $N$ heterogeneous compute nodes:
$$\mathcal{N} = \{n_1, n_2, \dots, n_N\}$$
connected over an unmanaged local area network (LAN / Wi-Fi) characterized by time-varying round-trip times $\text{RTT}_i(t)$ and fluctuating bandwidth $B_i(t)$.

Each node $n_i$ possesses a dynamic capability vector:
$$\mathbf{c}_i(t) = \langle C_i, F_i, M_i, G_i, V_i, U_i(t), L_i(t) \rangle$$
where $C_i$ is CPU core count, $F_i$ is CPU clock frequency, $M_i$ is total available memory, $G_i \in \{0, 1\}$ indicates dedicated GPU availability, $V_i$ is GPU VRAM, $U_i(t) \in [0, 1]$ is real-time resource utilization, and $L_i(t)$ is local queue load.

Arriving tasks form an asynchronous stream:
$$\mathcal{T} = \{t_1, t_2, \dots\}$$
where each task $t_j$ is characterized by requirements:
$$\mathbf{r}_j = \langle \text{type}_j, P_j, \text{gpu\_req}_j, \text{mem\_req}_j, D_j, S_j, \pi_j \rangle$$
where $P_j$ is task priority, $\text{gpu\_req}_j$ is GPU necessity, $\text{mem\_req}_j$ is minimum RAM, $D_j$ is timeout deadline, $S_j$ is binary payload size in bytes, and $\pi_j \in \{\text{local\_only}, \text{wireless\_allowed}, \text{remote\_allowed}\}$ is the privacy/offload policy.

### The Objective Function
The fundamental objective of TaskMesh is to find an online mapping function:
$$f: (\mathcal{T} \times \mathcal{N}) \to n^* \in \mathcal{N}$$
at each time step $t$ such that:
1. **Total Task Turnaround Latency is Minimized**:
   $$\min \sum_{j} \left( T_{\text{completion}}(t_j) - T_{\text{submission}}(t_j) \right)$$
2. **Cluster Throughput is Maximized**:
   $$\max \frac{|\mathcal{T}_{\text{completed}}|}{\Delta t}$$
3. **Node Starvation is Prevented (Fairness Guaranteed)**:
   The coefficient of variation (CV) of task allocations across nodes remains strictly bounded:
   $$\text{CV}_{\text{alloc}} = \frac{\sigma(\text{alloc})}{\mu(\text{alloc})} \le \epsilon_{\text{fairness}}$$
   ensuring that faster nodes do not greedily starve slower nodes when capacity permits.
4. **Network Offload Overhead Does Not Exceed Local Execution Time**:
   A remote offload is dispatched if and only if:
   $$T_{\text{remote}}(t_j, n_{\text{remote}}) < T_{\text{local}}(t_j, n_{\text{local}})$$
   where:
   $$T_{\text{remote}} = T_{\text{upload}}(S_j, B_{\text{up}}) + \text{RTT} + T_{\text{remote\_queue}} + T_{\text{remote\_infer}} + T_{\text{download}}$$
   $$T_{\text{local}} = T_{\text{local\_queue}} + T_{\text{local\_infer}}$$

---

## 5. Proposed Solution: The TaskMesh Architecture

TaskMesh resolves this multi-objective optimization problem through an interconnected set of decoupled subsystems:

1. **Lightweight Central Control Plane (`OrchestratorRuntime`)**:
   An asynchronous event loop orchestrates global state, backed by durable relational storage (SQLite/PostgreSQL) and an in-memory priority queue.
2. **Persistent Full-Duplex Network Transport**:
   Compute nodes connect over persistent WebSockets, eliminating the high polling overhead of REST or message broker worker loops. The protocol exchanges typed JSON envelopes for control events and raw 48-byte framed binary chunks (`TMCH`) for multi-megabyte image payloads.
3. **Multi-Stage Adaptive Scheduling Pipeline**:
   Instead of relying on a monolithic heuristic or an unpredictable black-box deep neural network, TaskMesh constructs a pipeline of specialized, mathematically grounded stages:
   - **Hard Constraint Filter**: Removes offline, draining, or under-specified nodes.
   - **DRR Fairness Gate**: Maintains deficit counters with adaptive quanta; nodes without sufficient deficit are gated until round exhaustion, preventing starvation.
   - **Contract-Net Suitability Bidding**: Evaluates candidate suitability across 5 balanced dimensions.
   - **MWU Factor Weight Adaptation**: Dynamically shifts factor weights online based on observed task execution losses.
   - **Tabular Q-Learning**: Explores and exploits selection among top candidate ranks using candidate-slot actions that remain invariant to dynamic node IDs.
   - **Wireless Cost Comparison**: Measures real-time network latency and upload bandwidth via EWMA, enforcing local execution when network transfer costs exceed remote acceleration gains.
4. **End-to-End Fault Tolerance Engine**:
   Task execution is guarded by attempt IDs and expiring leases. Node disconnects trigger immediate task reclamation, checkpoint state re-attachment, and re-queuing. Irrecoverable poison tasks are isolated into a Dead-Letter Queue (DLQ). Primary orchestrator failure triggers automated failover to a warm Standby replica.

---

## 6. Intended Users & Real-World Use Cases

### 6.1 Intended Users
- **AI & Robotics Researchers**: Academics running vision models, reinforcement learning, or sensor processing across distributed lab machines without access to enterprise Kubernetes clusters.
- **Edge System Engineers**: Developers building smart building, IoT, or industrial automation setups across mixed edge devices (Raspberry Pi, Jetson, NUC).
- **Computer Science Educators & Students**: A readable, fully tested Python codebase ideal for studying distributed systems, scheduling theory, and network protocols.
- **Privacy-Conscious Organizations**: Small enterprises requiring private, air-gapped distributed computing without sending internal data to third-party cloud APIs.

### 6.2 Concrete Real-World Scenarios
1. **Smart Campus Surveillance with Camera Offloading**:
   A battery-powered Raspberry Pi with a camera captures high-resolution video frames. Because running YOLOv8 on the Pi CPU takes 450ms per frame (2.2 FPS), the Pi acts as a TaskMesh client. It offloads frames to a desktop GPU workstation across the local Wi-Fi. If Wi-Fi degrades and transfer time climbs past 300ms, TaskMesh's `NetworkEstimator` automatically switches to local low-resolution inference, ensuring uninterrupted monitoring.
2. **Collaborative Research Laboratory Computing**:
   A 5-person research group connects their individual development laptops and two shared GPU servers into a TaskMesh cluster. When a student submits a batch of 500 computational simulations, TaskMesh distributes the workload proportionally: the GPU servers handle heavy matrix jobs, while developer laptops process lightweight CPU tests during idle periods without starving any single machine.
3. **Air-Gapped Industrial Quality Inspection**:
   In a manufacturing facility with no external Internet access, inspection sensors photograph assembly line items. TaskMesh coordinates inspection tasks across three on-premise industrial PCs. If one PC suffers a hardware failure, TaskMesh detects the missing heartbeat within seconds and seamlessly reroutes unfinished inspection tasks to the surviving machines.

---

## 7. Current Project Limitations

To maintain architectural honesty, the following real limitations of the current TaskMesh implementation must be recognized:

1. **Local Network Boundary**: TaskMesh is designed for local area networks (LAN / Wi-Fi) on the same IP subnet. It does not include NAT traversal (STUN/TURN/ICE) or multi-region routing.
2. **Centralized Orchestrator Single-Point Bottleneck**: Although High Availability is supported via Warm-Standby failover, the control plane is centralized. TaskMesh does not use fully decentralized peer-to-peer consensus (e.g., Paxos/Raft mesh).
3. **Single Task Decomposition**: TaskMesh currently schedules independent, atomic tasks. It does not natively construct Directed Acyclic Graph (DAG) pipelines where task B automatically consumes intermediate tensor outputs of task A without returning to the orchestrator.
4. **Static In-Memory Security**: While HMAC-SHA256 signing and replay protection are fully implemented, TaskMesh currently relies on a shared cluster secret token rather than per-node asymmetric public/private key infrastructure (PKI) or automated TLS certificate rotation.

