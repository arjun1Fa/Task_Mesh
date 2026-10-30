++# TaskMesh — Setup and Execution Guide

## 1. System Requirements & Prerequisites

### 1.1 Operating Systems Supported
- **Windows**: Windows 10 / Windows 11 / Windows Server (PowerShell 5.1+ or PowerShell Core 7+).
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora, Arch Linux (Bash / Zsh).
- **macOS**: macOS 12+ (Monterey, Ventura, Sonoma) on Apple Silicon (M1/M2/M3) or Intel.

### 1.2 Software Prerequisites
- **Python**: Python 3.11, 3.12, 3.13, or 3.14 (64-bit).
- **Git**: Installed and available on your system `PATH`.
- **C/C++ Build Tools** (Optional, only needed if compiling PyTorch or OpenCV from source).

---

## 2. Installation & Virtual Environment Setup

### 2.1 Clone the Repository
```bash
git clone https://github.com/your-org/TASK_MESH.git
cd TASK_MESH
```

### 2.2 Create & Activate Python Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If script execution is disabled on Windows: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

#### On Linux / macOS (Bash/Zsh):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Install TaskMesh Dependencies

#### Core Orchestration & Networking (Minimal Footprint):
```bash
pip install -e .
```

#### With AI Acceleration (PyTorch, Ultralytics YOLOv8, OpenCV):
```bash
pip install -e ".[ai]"
```

#### With Developer & Testing Tools (pytest, pytest-asyncio):
```bash
pip install -e ".[test]"
```

---

## 3. Quick Start: Single-Command Local Cluster Launcher

To test real distributed multi-process execution on a single computer without setting up multiple physical machines, use the built-in development cluster launcher:

```bash
taskmesh-cluster --nodes 3 --port 8000
```

This single command:
1. Starts the primary Orchestrator on `http://127.0.0.1:8000` (WebSocket at `ws://127.0.0.1:8000/v1/ws/nodes`).
2. Spawns 3 independent Node Agent processes in separate OS processes:
   - `node-alpha` (tagged `gpu,cuda`)
   - `node-beta` (tagged `cpu,general`)
   - `node-gamma` (tagged `cpu,general`)
3. Connects all 3 nodes via WebSockets, begins heartbeat exchanges, and opens the cluster for task submission.
4. Press `Ctrl+C` to terminate all processes cleanly.

---

## 4. Multi-Machine Physical LAN Setup

To pool compute resources across different physical computers on the same local Wi-Fi or Ethernet network:

### 4.1 Step 1: Identify Host IP & Configure Firewall

On the machine hosting the Orchestrator (e.g. Machine A), find its local LAN IP address:
- **Windows**: `ipconfig` (look for IPv4 Address under Wi-Fi or Ethernet, e.g. `192.168.1.100`).
- **Linux/macOS**: `ip route get 1.1.1.1` or `ifconfig`.

#### Configure Inbound Firewall:
- **Windows (PowerShell as Administrator)**:
  ```powershell
  New-NetFirewallRule -DisplayName "TaskMesh Orchestrator" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
  ```
- **Linux (UFW)**:
  ```bash
  sudo ufw allow 8000/tcp
  ```

### 4.2 Step 2: Start Orchestrator on Machine A (Host)
Bind the orchestrator to `0.0.0.0` so it listens on all local network interfaces:

```bash
# Insecure development mode:
taskmesh-server --host 0.0.0.0 --port 8000 --mode adaptive

# Secure mode (with HMAC authentication):
taskmesh-server --host 0.0.0.0 --port 8000 --mode adaptive --secure --token my-secret-cluster-token
```

### 4.3 Step 3: Connect Worker Nodes on Machine B, C, etc.
On each worker computer, launch a Node Agent targeting Machine A's LAN IP:

```bash
# Worker Laptop (Machine B)
taskmesh-node --node-id laptop-worker --url ws://192.168.1.100:8000/v1/ws/nodes --workers 4

# GPU Workstation (Machine C - Secure Mode)
taskmesh-node --node-id gpu-workstation --url ws://192.168.1.100:8000/v1/ws/nodes --workers 8 --secure --token my-secret-cluster-token --tags "gpu,cuda,vision"
```

---

## 5. Setting Up Primary / Standby High Availability (Failover)

To run TaskMesh in active-passive high availability:

1. **Machine 1: Start Primary Orchestrator (Port 8000)**:
   ```bash
   taskmesh-server --port 8000 --mode adaptive
   ```

2. **Machine 2: Start Standby Orchestrator (Port 8001)**:
   ```bash
   taskmesh-server --port 8001 --standby --primary-url http://192.168.1.100:8000 --snapshot-interval 1.0
   ```

3. **Start Worker Nodes with Failover Target**:
   ```bash
   taskmesh-node --node-id node-1 --url ws://192.168.1.100:8000/v1/ws/nodes --standby-url ws://192.168.1.101:8001/v1/ws/nodes
   ```

*Testing Failover*: Kill the Primary process (`Ctrl+C` or `taskkill`). Observe Standby logs: after 3 failed probes, the Standby automatically promotes to Primary, and the worker node reconnects to port 8001 without dropping active work.

---

## 6. Submitting Workloads & Managing the Cluster

TaskMesh provides a dedicated CLI management tool: `taskmeshctl`.

### 6.1 Check Cluster Health & Connected Nodes
```bash
# View cluster status, running tasks, fairness metric
taskmeshctl cluster health

# List registered compute nodes
taskmeshctl node list

# Inspect hardware specs & telemetry of a specific node
taskmeshctl node inspect node-alpha
```

### 6.2 Discover Nodes on Local Wi-Fi (UDP Broadcast)
```bash
taskmeshctl discover --timeout 2.0
```

### 6.3 Submit Computational Tasks
```bash
# Submit a lightweight logging task
taskmeshctl task submit --type log --payload '{"message": "Hello from TaskMesh"}' --priority 10

# Submit a CPU-intensive test task (50,000 iterations)
taskmeshctl task submit --type cpu_test --payload '{"iterations": 50000}' --priority 5

# Submit an AI vision task requiring GPU acceleration
taskmeshctl task submit --type image_inference --payload '{"model": "yolov8n", "image_dim": 640}' --gpu
```

### 6.4 Submit Real Image Files for Wireless AI Offloading
```bash
taskmeshctl task submit-image --image path/to/photo.jpg --model yolov8n --priority 10 --policy wireless_allowed
```

### 6.5 Inspect & Cancel Tasks
```bash
# List all recent tasks
taskmeshctl task list

# Query task result by ID
taskmeshctl task get <TASK_ID>

# Cancel an active task
taskmeshctl task cancel <TASK_ID>

# Retry a failed task
taskmeshctl task retry <TASK_ID>
```

### 6.6 Access the Web Dashboard UI
Open your browser to:
```text
http://localhost:8000/
```
The built-in web dashboard provides real-time KPI metrics, online node cards, live task lists with status badges, and interactive scheduler explainability charts.

Interactive OpenAPI documentation is available at:
```text
http://localhost:8000/docs
```

---

## 7. Running Verification Tests & Benchmarks

### 7.1 Running the Automated Test Suite
```bash
python -m pytest tests/ -v
```

### 7.2 Running Scheduler Microbenchmarks
```bash
python benchmarks/benchmark_schedulers.py
```

### 7.3 Running Distributed Multi-Process Benchmark
```bash
python benchmarks/benchmark_distributed.py
```

### 7.4 Running End-to-End Wi-Fi Verification Script
To verify physical offload between two laptops on your Wi-Fi:
```bash
python scripts/manual_wifi_test.py --orchestrator http://192.168.1.100:8000 --image my_photo.jpg
```

---

## 8. Troubleshooting & Common Errors

| Issue / Error Message | Root Cause | Verified Solution |
|---|---|---|
| `ConnectionRefusedError: [Errno 111] Connection refused` | Orchestrator is not running or node is pointing to the wrong IP/port. | Verify orchestrator process is active. Confirm IP address via `ipconfig` or `ifconfig`. |
| `WebSocket connection failed: 1008 Policy Violation` | Join token mismatch between node and orchestrator. | Ensure `--token` on `taskmesh-node` matches `--token` on `taskmesh-server` (or both omitted). |
| `taskmeshctl: error: unable to connect to TaskMesh Orchestrator` | CLI defaults to `http://127.0.0.1:8000`. | If running on another machine, pass `--url http://<LAN_IP>:8000`. |
| `No eligible nodes available for task task_xxx` | Task requirements (e.g. `--gpu`) exceed capabilities of connected nodes. | Connect a node with GPU acceleration, or submit without `--gpu`. |
| `Windows Firewall block: connection times out` | Windows Defender blocks inbound port 8000. | Run PowerShell command in Section 4.1 to allow inbound TCP 8000. |
| `ModuleNotFoundError: No module named 'pytest'` | Test dependencies not installed in current environment. | Run `pip install pytest pytest-asyncio` inside your `.venv`. |
