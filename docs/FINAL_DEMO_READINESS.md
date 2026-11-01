# TaskMesh — Final Demonstration & Deployment Readiness Guide

**Date:** November 1, 2026  
**System:** TaskMesh Distributed Orchestration Framework  
**Status:** **READY FOR LIVE DEMONSTRATION**

---

## 1. System Overview & Access URLs

TaskMesh is configured with standalone frontends served both directly through embedded FastAPI/Uvicorn static mounts and via Vite development servers.

| Component | Architecture Role | Embedded / Production URL | Dev Server URL |
| :--- | :--- | :--- | :--- |
| **Orchestrator Control Center** | Central scheduling, cluster topology, task dispatch | `http://localhost:8000/` | `http://localhost:5173/` |
| **Worker Alpha Console** | Dedicated execution agent for `node-alpha` | `http://localhost:8081/` | `http://localhost:5174/` |
| **Worker Beta Console** | Dedicated execution agent for `node-beta` | `http://localhost:8082/` | Port reconfigurable |

---

## 2. Startup Commands

### Step A: Start the Central Orchestrator
Open a terminal (Machine A or Terminal 1):
```bash
# Start Orchestrator backend (serves API on port 8000 and embedded React UI)
python -m taskmesh.orchestrator.main --port 8000 --host 0.0.0.0
```
*Health Check:* `http://localhost:8000/v1/cluster/health`

### Step B: Start Worker Agent Alpha
Open a terminal (Machine B or Terminal 2):
```bash
# Start Worker Alpha connecting to the orchestrator WebSocket hub
python -m taskmesh.node.main \
  --node-id node-alpha \
  --url ws://127.0.0.1:8000/v1/ws/nodes \
  --console-port 8081 \
  --console-host 0.0.0.0
```
*Console Check:* `http://localhost:8081/`

### Step C: Start Worker Agent Beta
Open a terminal (Machine C or Terminal 3):
```bash
# Start Worker Beta connecting to the orchestrator WebSocket hub
python -m taskmesh.node.main \
  --node-id node-beta \
  --url ws://127.0.0.1:8000/v1/ws/nodes \
  --console-port 8082 \
  --console-host 0.0.0.0
```
*Console Check:* `http://localhost:8082/`

---

## 3. End-to-End Task Submission Demonstration

Follow these steps to demonstrate real distributed task dispatch:

1. **Open Orchestrator Control Center:**
   Navigate to `http://localhost:8000/`.
   - Observe both `node-alpha` and `node-beta` listed as **ONLINE** in the **Nodes** panel.
   - Note the hardware specifications (CPU cores, memory, GPU availability) dynamically gathered from each agent.

2. **Open Worker Consoles:**
   - In a second browser window, navigate to `http://localhost:8081/` (Worker Alpha Console).
   - In a third browser window, navigate to `http://localhost:8082/` (Worker Beta Console).
   - Verify that each console strictly displays its own node ID (`node-alpha` vs `node-beta`).

3. **Submit a Task via the Orchestrator UI:**
   - On `http://localhost:8000/`, click **"Submit Task"**.
   - The modal automatically defaults to:
     - **Task Type:** `image_inference`
     - **Priority:** `MEDIUM`
     - **Payload:**
       ```json
       {
         "model": "yolov8n",
         "batch_size": 1
       }
       ```
   - Click **"Submit"**.

4. **Observe Dynamic Scheduling & Real-Time WebSocket Streaming:**
   - The Orchestrator's adaptive scheduler (MWU + Q-learning + DRR) scores both workers and selects the optimal node.
   - The task transitions: `PENDING` -> `ASSIGNED` -> `RUNNING` -> `COMPLETED`.
   - Real-time updates appear immediately via the `/v1/ws/dashboard` WebSocket connection.

5. **Verify Worker Isolation & Execution Telemetry:**
   - On the selected worker's console (e.g., Worker Alpha at `http://localhost:8081/tasks`):
     - The task appears in the **Active** table and transitions to **Completed**.
     - Execution time, timestamps, and model output metadata are displayed.
   - On the other worker's console (e.g., Worker Beta at `http://localhost:8082/tasks`):
     - The task list remains completely empty. Worker Beta has zero knowledge of Worker Alpha's task.

---

## 4. Worker Failure and Failover Demonstration

1. **Simulate a Worker Node Crash:**
   - In Terminal 2 (Worker Alpha), press `Ctrl+C` to terminate the process.
2. **Observe Orchestrator Reaction:**
   - Within 1–3 heartbeat intervals, the Orchestrator marks `node-alpha` as **OFFLINE**.
   - An event `node.disconnected` is broadcast to the Orchestrator dashboard.
3. **Submit a Second Task:**
   - Submit another `image_inference` or `cpu_test` task via the Orchestrator UI.
   - The scheduler recognizes `node-alpha` is unreachable and automatically routes the task exclusively to `node-beta`.
   - Worker Beta executes the task immediately.
4. **Rejoin the Cluster:**
   - Restart Worker Alpha in Terminal 2.
   - Worker Alpha re-establishes the WebSocket connection with its HMAC credential.
   - The Orchestrator marks `node-alpha` as **ONLINE** and immediately resumes balanced task distribution.

---

## 5. Supported Task Types & Payloads

The Worker Agent execution pool supports the following native task handlers:

| Task Type | Description | Example Payload |
| :--- | :--- | :--- |
| `image_inference` | YOLOv8 / Neural Network inference execution | `{"model": "yolov8n", "batch_size": 1}` |
| `cpu_test` | Compute benchmark / matrix multiplication | `{"matrix_size": 256, "iterations": 5}` |
| `sleep` | Non-blocking simulated latency / queue testing | `{"duration": 2.0}` |
| `log` | Diagnostic telemetry logging | `{"message": "Worker verification ping"}` |

---

## 6. Physical LAN Deployment Status

| Category | Readiness Status | Details |
| :--- | :--- | :--- |
| **Multi-Process Local Test** | **VERIFIED WORKING** | Tested with 3 independent OS processes across local loopback ports (8000, 8081, 8082). |
| **Cross-Host LAN Binding** | **READY** | All services bind to `0.0.0.0` or custom `--lan-ip`. Replace `127.0.0.1` with Machine A's LAN IP (e.g., `ws://192.168.1.50:8000/v1/ws/nodes`). |
| **Authentication & Security** | **READY** | Node connections require pre-shared secrets (`HMAC-SHA256`) and anti-replay nonce timestamps to prevent unauthorized agents from joining over Wi-Fi/LAN. |
| **Auto-Discovery** | **READY** | UDP broadcast discovery advertiser/listener in `taskmesh.discovery.broadcast` operates on port 8001 across standard LAN broadcast addresses. |
| **Physical LAN Verification** | **PENDING MULTI-DEVICE SETUP** | Requires deploying onto at least 2 distinct physical hardware hosts (e.g., laptop + desktop over local Wi-Fi router). |

---

## 7. Known Limitations & Notes

1. **Embedded Console Server:** The Worker Console API runs as an asynchronous task (`asyncio.Task`) within the `NodeAgent` Python process rather than a distinct secondary OS daemon. This is intentional to provide unified memory access to `agent.task_history` and hardware sensors while exposing a dedicated HTTP port (8081, 8082, etc.).
2. **WebSocket Fallback:** If the browser loses the dashboard WebSocket connection, the React UI automatically polls `/v1/cluster/health` and `/v1/tasks` every 5 seconds to guarantee eventual consistency.
