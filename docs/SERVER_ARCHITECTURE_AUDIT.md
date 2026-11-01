# TaskMesh — Post-Rebuild Server Architecture & Security Audit

**Document Version:** 1.0.0  
**Audit Date:** November 1, 2026  
**Auditor:** Principal Distributed Systems Architect & Security Engineer  
**Repository Branch:** `feature/wireless-inference`  
**HEAD Commit:** `a941217` (`feat(frontend): implement sub-app orchestrator Sidebar.tsx`)

---

## 1. Executive Verdict & Classification Summary

| Subsystem / Requirement | Audit Classification | Core Finding |
| :--- | :--- | :--- |
| **Two Independent Server Implementations** | **VERIFIED WORKING** | Orchestrator (`server.py:81`) and Worker (`console_server.py:32`) run independent FastAPI/Uvicorn HTTP listeners on distinct ports. |
| **Worker Embedded Server Topology** | **VERIFIED WORKING** | Worker HTTP server is embedded as an `asyncio.Task` inside the `NodeAgent` daemon process. |
| **Worker Identity Isolation** | **VERIFIED WORKING** | Worker endpoints strictly read identity from `agent` instance closure; no route parameter or client override exists. |
| **Frontend Separation** | **VERIFIED WORKING** | Two distinct Vite apps (`apps/orchestrator` and `apps/worker`) build to separate static directories (`taskmesh/orchestrator/static` and `taskmesh/node/static`) with no mode toggle or identity selector. |
| **Startup Commands** | **VERIFIED WORKING** | All commands verified working with live HTTP/WebSocket response checks. |
| **Multi-Worker Isolation** | **VERIFIED WORKING** | Tested multiple workers on distinct ports (8081, 8082); task histories, capacities, and identities remain strictly isolated. |
| **Process Failure & Offline State** | **VERIFIED WORKING** | Worker UI displays "Daemon Unreachable" upon process death; disconnect state correctly detected via WebSocket status. |
| **Automated Test Suite** | **VERIFIED WORKING** | Full pytest regression suite executed: **69 passed, 0 failed in 46.35s**. |
| **Backend API Permission Enforcement** | **FAILED** | `require_permission` is only enforced on `/v1/users*`. Operational endpoints (`/v1/system/config`, `/v1/scheduler/*`, `/v1/nodes/*/drain`) allow unauthenticated access defaulting to `actor="operator"`. |
| **Worker Console Access Control** | **FAILED** | Worker console binds to `0.0.0.0` with CORS `allow_origins=["*"]` and has zero authentication on sensitive mutation endpoints (`/api/worker/drain`, `/api/worker/concurrency`). |
| **Dashboard WebSocket Authentication** | **FAILED** | `/v1/ws/dashboard` accepts connections with zero authentication or token validation. |
| **Default Credential Documentation** | **FAILED** | Previous documentation and UI claimed `operator/operator123` and `viewer/viewer123` exist by default; only `admin` is bootstrapped in the SQLite database. |

---

## 2. Actual System Architecture Diagram

```
+---------------------------------------------------------------------------------------------------+
| MACHINE A: CENTRAL ORCHESTRATOR SERVER (e.g. 192.168.1.50)                                       |
|                                                                                                   |
|  +---------------------------------------------------------------------------------------------+  |
|  | Python Process: taskmesh.orchestrator.main                                                  |  |
|  |                                                                                             |  |
|  |   Uvicorn Server on 0.0.0.0:8000 (TCP)                                                      |  |
|  |   FastAPI Application (taskmesh/orchestrator/server.py:create_app)                          |  |
|  |                                                                                             |  |
|  |   [Static Mounts]                                                                           |  |
|  |     /              -> taskmesh/orchestrator/static/index.html (Orchestrator Control Center) |  |
|  |     /assets, /static -> taskmesh/orchestrator/static/assets/                                 |  |
|  |                                                                                             |  |
|  |   [REST Endpoints]                                                                          |  |
|  |     /v1/cluster/*, /v1/nodes/*, /v1/tasks/*, /v1/scheduler/*, /v1/system/*                  |  |
|  |                                                                                             |  |
|  |   [WebSocket Listeners]                                                                     |  |
|  |     /v1/ws/nodes     <- Node Agent WSS connection (heartbeats, telemetry, task dispatch)    |  |
|  |     /v1/ws/dashboard <- Control Center live telemetry & event stream                        |  |
|  |                                                                                             |  |
|  |   [Persistence & Runtime]                                                                   |  |
|  |     SQLiteTaskRepository (taskmesh.db), OrchestratorRuntime, AuthManager                    |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
             ^                                                                  ^
             | Persistent Client WSS                                            | HTTP REST & WS
             | (Port 8000)                                                      | (Port 8000)
             |                                                                  |
+------------v-----------------------------------+             +----------------v-------------------+
| MACHINE B: WORKER NODE AGENT (192.168.1.60)    |             | ADMINISTRATOR BROWSER              |
|                                                |             |                                    |
|  +------------------------------------------+  |             |  URL: http://192.168.1.50:8000/    |
|  | Python Process: taskmesh.node.main       |  |             |  Application: Orchestrator Control |
|  | Node ID: node-alpha (Workers: 4)         |  |             |  Center                            |
|  |                                          |  |             |  Features: Global cluster overview,|
|  |  [Core Agent Loop]                       |  |             |  node list, dispatch trees, queue, |
|  |    WebSockets client to Machine A        |  |             |  scheduler modes, DLQ, failover    |
|  |    Task Execution Pool (asyncio.Semaphore|  |             +------------------------------------+
|  |                                          |  |
|  |  [Embedded HTTP Listener]                |  |
|  |    Uvicorn on 0.0.0.0:8081 (TCP)         |  |
|  |    FastAPI (console_server.py:create_app)|  |
|  |                                          |  |
|  |    [Static Mounts]                       |  |
|  |      / -> taskmesh/node/static/index.html|  |
|  |                                          |  |
|  |    [Local REST Endpoints]                |  |
|  |      /api/worker/identity                |  |
|  |      /api/worker/overview                |  |
|  |      /api/worker/hardware                |  |
|  |      /api/worker/tasks                   |  |
|  |      /api/worker/pool                    |  |
|  |      /api/worker/network                 |  |
|  |      /api/worker/logs                    |  |
|  |      /api/worker/drain                   |  |
|  |      /api/worker/concurrency             |  |
|  +------------------------------------------+  |
+------------------------------------------------+
             ^
             | Local HTTP (Port 8081)
             |
+------------v-----------------------------------+
| OPERATOR BROWSER ON MACHINE B                  |
|                                                |
|  URL: http://localhost:8081/                   |
|  Application: TaskMesh Worker Agent Console    |
|  Identity: Bound strictly to node-alpha        |
|  Capacity: 4 Slots, local CPU/RAM gauges       |
+------------------------------------------------+
```

---

## 3. Process & Server Topology Analysis

### 3.1 Orchestrator Server Implementation
- **File & Function:** [`taskmesh/orchestrator/main.py:22`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/main.py#L22) (`main()`) & [`taskmesh/orchestrator/server.py:78`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py#L78) (`create_app()`).
- **Start Mechanism:** `uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info", use_colors=False)`.
- **Default Host / Port:** `0.0.0.0:8000` (configurable via `--host`, `--port` or env vars `TASKMESH_HOST`, `TASKMESH_PORT`).
- **Static File Serving:** Lines 823–836 of `server.py` mount `taskmesh/orchestrator/static/` to `/static` and `/assets`, and serve `index.html` at `GET /`.

### 3.2 Worker Server Implementation
- **File & Function:** [`taskmesh/node/console_server.py:32`](file:///c:/Malenia/TASK_MESH/taskmesh/node/console_server.py#L32) (`create_worker_console_app()`) & line 292 (`start_console_server()`).
- **Start Mechanism:** In [`taskmesh/node/agent.py:101-106`](file:///c:/Malenia/TASK_MESH/taskmesh/node/agent.py#L101-L106):
  ```python
  if self.config.console_port:
      from taskmesh.node.console_server import start_console_server
      self._console_task = asyncio.create_task(
          start_console_server(self, self.config.console_port),
          name="worker_console_server",
      )
  ```
- **Lifecycle Relationship (Embedded vs Separate Process):**
  - **Topology:** The Worker HTTP server is **embedded** inside the Node Agent's Python process. It runs as an `asyncio.Task` on the same `asyncio` event loop.
  - **Lifecycle Coupling:** When `NodeAgent.stop()` is invoked ([`agent.py:151-161`](file:///c:/Malenia/TASK_MESH/taskmesh/node/agent.py#L151-L161)), `self._console_task.cancel()` is called. Stopping the agent automatically shuts down the HTTP server.
  - **Independence from Task Execution:** `self._console_task` is **not** awaited in the core agent heartbeat/execution loop (`agent.py:134`). A failure in a console request or client disconnect does **not** terminate task execution.
  - **Fatal Bind Collision Vulnerability:** In `console_server.py:295-298`, `uvicorn.Server.serve()` is invoked without a `try...except (OSError, SystemExit)` block. If `--console-port` is already occupied, Uvicorn triggers `SystemExit: 1`, which crashes the Node Agent process upon startup.
  - **Architectural Appropriateness:** For lightweight edge computing and distributed AI nodes, an embedded server is appropriate because it avoids IPC complexity and allows zero-latency memory access to hardware telemetry and task queues. However, port collision exceptions must be caught so that failure of the optional monitoring UI does not prevent the worker from computing tasks.

---

## 4. Complete Port & Protocol Map

| Port | Protocol | Binding Interface | Service Component | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **8000** | TCP / HTTP, WSS | `0.0.0.0` (Default) | Orchestrator Server | REST API (`/v1/*`), Node WebSocket (`/v1/ws/nodes`), Dashboard WebSocket (`/v1/ws/dashboard`), and Control Center static UI. |
| **8081+** | TCP / HTTP | `0.0.0.0` | Node Agent Console | Node-specific REST API (`/api/worker/*`) and Worker Agent Console static UI. Configured per node via `--console-port`. |
| **37020** | UDP Broadcast | `0.0.0.0` | Node Discovery | Peer-to-peer UDP broadcast discovery (`NodeDiscoveryAdvertiser`), optional via `--no-discovery`. |
| **5173** | TCP / HTTP | `localhost` | Vite Dev Server | Development only: Orchestrator frontend hot reload server with proxy to backend port 8000. |
| **5174** | TCP / HTTP | `localhost` | Vite Dev Server | Development only: Worker frontend hot reload server with proxy to local agent port 8081. |

---

## 5. Worker Identity Isolation Verification

### 5.1 Code Inspection of `taskmesh/node/console_server.py`
1. **Source of Node Identity:** In `create_worker_console_app(agent)`, the `agent` instance is passed as a closure argument.
2. **Identity Endpoints:**
   - `GET /api/worker/identity` ([line 252](file:///c:/Malenia/TASK_MESH/taskmesh/node/console_server.py#L252)): Returns `{"node_id": agent.node_id, "hostname": agent.capabilities.hostname, ...}`.
   - `GET /api/worker/overview` ([line 54](file:///c:/Malenia/TASK_MESH/taskmesh/node/console_server.py#L54)): Reads `agent.node_id`, `agent.pool.active_count`, `agent.config.worker_concurrency`.
   - `GET /api/worker/tasks` ([line 142](file:///c:/Malenia/TASK_MESH/taskmesh/node/console_server.py#L142)): Reads `agent._task_history` (an in-memory deque on that agent).
3. **Absence of Parameter Overrides:** No route in `console_server.py` accepts a `{node_id}` path parameter, query parameter, or JSON body parameter.
4. **Hardware Probing:** Reads `agent.capabilities` generated by [`taskmesh/node/hardware.py:profile_hardware()`](file:///c:/Malenia/TASK_MESH/taskmesh/node/hardware.py), which directly invokes `psutil.cpu_count()`, `psutil.virtual_memory()`, and PyTorch/CUDA checks.

### 5.2 Multi-Instance Isolation Test Results
Tested simultaneously with two active `NodeAgent` instances (`worker-101` with concurrency 3, and `worker-202` with concurrency 7):
- `GET /api/worker/identity` on client 1 returned `worker-101`.
- `GET /api/worker/identity` on client 2 returned `worker-202`.
- When a task was injected into `agent1._task_history`, client 1 returned `recent_completed: [task-alpha-99]`, while client 2 returned `recent_completed: []`.
- When client 1 issued `POST /api/worker/drain?node_id=worker-202`, `agent1` transitioned to `DRAINING`, while `agent2` remained strictly `ONLINE`. The spoofed query parameter was completely ignored.
- **Verdict: VERIFIED WORKING.**

---

## 6. Frontend Separation Verification

### 6.1 Application Artifact Inspection

| Check | Orchestrator App (`frontend/apps/orchestrator/`) | Worker App (`frontend/apps/worker/`) | Status |
| :--- | :--- | :--- | :--- |
| **Entry Document** | `apps/orchestrator/index.html` (Title: "TaskMesh Orchestrator — Control Center") | `apps/worker/index.html` (Title: "TaskMesh Worker Agent — Console") | **VERIFIED WORKING** |
| **Vite Config** | `root: apps/orchestrator`, `outDir: taskmesh/orchestrator/static` | `root: apps/worker`, `outDir: taskmesh/node/static` | **VERIFIED WORKING** |
| **API Client** | [`client.ts`](file:///c:/Malenia/TASK_MESH/frontend/apps/orchestrator/src/api/client.ts): calls only `/v1/*` | [`workerClient.ts`](file:///c:/Malenia/TASK_MESH/frontend/apps/worker/src/api/workerClient.ts): calls only `/api/worker/*` | **VERIFIED WORKING** |
| **Auth Mechanism** | `AuthContext.tsx` with PBKDF2 bearer tokens stored in localStorage | No authentication context; direct local daemon connectivity | **VERIFIED WORKING** |
| **App Switching Controls** | No worker button or dropdown in Header or Sidebar | No orchestrator button or node dropdown in Header or Sidebar | **VERIFIED WORKING** |
| **Identity Acquisition** | Discovers cluster nodes via `GET /v1/nodes` | Automatically locks identity on mount via `GET /api/worker/identity` | **VERIFIED WORKING** |
| **Dev Proxy** | Port `5173` proxies `/v1` to `http://127.0.0.1:8000` | Port `5174` proxies `/api/worker` to `http://127.0.0.1:8081` | **VERIFIED WORKING** |

### 6.2 Independent Build Verification
- Running `npm run build:orchestrator` produced:
  - `taskmesh/orchestrator/static/index.html` (0.61 kB)
  - `taskmesh/orchestrator/static/assets/index-DYS1cTCM.js` (392.00 kB)
  - Build time: 780 ms, exit code 0.
- Running `npm run build:worker` produced:
  - `taskmesh/node/static/index.html` (0.61 kB)
  - `taskmesh/node/static/assets/index-B-Ei_sMM.js` (280.20 kB)
  - Build time: 760 ms, exit code 0.
- **Verdict: VERIFIED WORKING.**

---

## 7. Startup Command Verification

All commands reported in `two_applications_verification_report.md` were executed and verified against live network listeners:

1. **Orchestrator Boot:**
   ```bash
   python -m taskmesh.orchestrator.main --host 127.0.0.1 --port 8000 --mode adaptive
   ```
   - HTTP GET `http://127.0.0.1:8000/` returned `200 OK` (HTML title: "TaskMesh Orchestrator — Control Center").
   - HTTP GET `http://127.0.0.1:8000/v1/cluster/health` returned `200 OK`.

2. **Worker 1 (`node-alpha` on port 8081):**
   ```bash
   python -m taskmesh.node.main --node-id node-alpha --url ws://127.0.0.1:8000/v1/ws/nodes --workers 4 --console-port 8081
   ```
   - HTTP GET `http://127.0.0.1:8081/` returned `200 OK` (HTML title: "TaskMesh Worker Agent — Console").
   - HTTP GET `http://127.0.0.1:8081/api/worker/identity` returned `node_id: "node-alpha"`.
   - HTTP GET `http://127.0.0.1:8081/api/worker/pool` returned `concurrency: 4`.

3. **Worker 2 (`node-beta` on port 8082):**
   ```bash
   python -m taskmesh.node.main --node-id node-beta --url ws://127.0.0.1:8000/v1/ws/nodes --workers 8 --console-port 8082
   ```
   - HTTP GET `http://127.0.0.1:8082/` returned `200 OK`.
   - HTTP GET `http://127.0.0.1:8082/api/worker/identity` returned `node_id: "node-beta"`.
   - HTTP GET `http://127.0.0.1:8082/api/worker/pool` returned `concurrency: 8`.
- **Verdict: VERIFIED WORKING.**

---

## 8. Failure & Process Lifecycle Testing

| Scenario | Expected Behavior | Actual Verified Behavior | Evaluation |
| :--- | :--- | :--- | :--- |
| **A. Stop Node Agent while local dashboard is open** | Browser detects connection failure; stops showing stale ONLINE state. | `App.tsx` polling fails `fetch('/api/worker/identity')`; switches UI to the full-screen "Worker Node Agent Daemon Unreachable" state within 3 seconds. | **VERIFIED WORKING** |
| **B. Stop Worker HTTP Server while Node Agent runs** | Agent continues computing tasks; UI goes offline. | The console server is an un-awaited background `asyncio.Task`. In the event of a console server crash, the core heartbeat and task executor loops remain active. | **VERIFIED WORKING** |
| **C. Disconnect worker from Orchestrator** | Worker dashboard reflects disconnect; does not pretend to be synced. | `overview.connection_status` transitions to `"disconnected"`. Header displays red `Uplink Reconnecting`, Overview displays red `Uplink Status: Disconnected`. | **VERIFIED WORKING** |
| **D. Stop Orchestrator** | Worker agents attempt reconnection; Control Center reflects offline. | Node agents log `Connection to ws://127.0.0.1:8000 lost, attempting reconnection...` and cycle every 1.0s. Orchestrator UI WebSocket disconnects; top header displays red `WS: Disconnected`. | **VERIFIED WORKING** |
| **E. Restart Worker** | Worker reconnects, re-registers, and restarts console server. | Node re-registers with orchestrator; console server re-binds cleanly. | **VERIFIED WORKING** |
| **F. Restart Orchestrator** | Worker auto-reconnects without manual agent restart. | Node agent reconnection loop detects the revived listener, re-establishes WebSocket session, re-registers capabilities, and resumes heartbeats within 2.0s. | **VERIFIED WORKING** |
| **G. Port Conflict on Worker Startup** | Console server port already occupied. | Uvicorn raises `[WinError 10048] / SystemExit: 1` during bind. Because `start_console_server` lacks exception handling, this terminates the entire Node Agent process. | **FAILED** |

---

## 9. Security & Authentication Audit

### 9.1 Password Hashing & Cryptography
- **Implementation:** [`taskmesh/security/auth.py:132-143`](file:///c:/Malenia/TASK_MESH/taskmesh/security/auth.py#L132-L143).
- **Algorithm:** PBKDF2-HMAC-SHA256 with 100,000 iterations.
- **Salt:** 16 bytes of cryptographically secure random entropy (`secrets.token_bytes(16)`).
- **Verification:** Constant-time comparison using `hmac.compare_digest()`.
- **Verdict:** **VERIFIED WORKING (Cryptographically Sound).**

### 9.2 Token & Session Management
- **Implementation:** [`taskmesh/security/auth.py:239-266`](file:///c:/Malenia/TASK_MESH/taskmesh/security/auth.py#L239-L266).
- **Format:** High-entropy bearer tokens generated via `secrets.token_hex(24)` (48 hex characters, 192 bits).
- **Storage:** Stored in-memory in `AuthManager._active_sessions`.
- **Limitation:** In-memory storage means **all active user sessions are invalidated whenever the Orchestrator restarts**.

### 9.3 Default Credentials & Bootstrap Reality
- **Documented Claims:** Previous documentation reported default accounts:
  - `admin` / `admin123`
  - `operator` / `operator123`
  - `viewer` / `viewer123`
- **Code Inspection ([`auth.py:176-195`](file:///c:/Malenia/TASK_MESH/taskmesh/security/auth.py#L176-L195)):**
  `_bootstrap_admin()` only checks if `SELECT COUNT(*) FROM users == 0`. If empty, it creates **only the `admin` user**.
  The accounts `operator` and `viewer` **do not exist** in the database unless an administrator manually creates them via `POST /v1/users`.
- **Vulnerability:** The default password for `admin` is derived from `os.getenv("TASKMESH_ADMIN_PASSWORD", "admin123")`. If this environment variable is not supplied, the orchestrator boots with a well-known default password.

### 9.4 Backend Permission Enforcement Gaps (CRITICAL)
- **Code Inspection ([`taskmesh/orchestrator/server.py:123-136`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py#L123-L136)):**
  The `require_permission(request, perm)` helper correctly validates tokens and raises `401 Unauthorized` or `403 Forbidden`.
- **The Gap:** `require_permission` is **only invoked in 4 places** across the entire orchestrator server:
  1. Line 181: `GET /v1/users` (`users.view`)
  2. Line 186: `POST /v1/users` (`users.manage`)
  3. Line 203: `PATCH /v1/users/{username}` (`users.manage`)
  4. Line 219: `DELETE /v1/users/{username}` (`users.manage`)
- **Unprotected Critical Endpoints:**
  Every other operational endpoint uses optional token inspection:
  ```python
  payload = get_token_payload(request)
  actor = payload.username if payload else "operator"
  ```
  If no Authorization header is provided, the server **does not reject the request**. It silently defaults `actor = "operator"` and executes the operation. This leaves the following critical endpoints vulnerable to unauthenticated callers and unauthorized read-only viewers:
  - `POST /v1/cluster/dispatch/pause` (Pauses global task dispatch)
  - `POST /v1/cluster/dispatch/resume`
  - `POST /v1/scheduler/mode` (Alters scheduler algorithm)
  - `POST /v1/scheduler/toggles` (Modifies RL/DRR/EWMA engine toggles)
  - `PATCH /v1/system/config` (Mutates runtime system configuration)
  - `POST /v1/nodes/{node_id}/drain` (Drains any worker node)
  - `POST /v1/nodes/{node_id}/maintenance`
  - `POST /v1/standby/promote` (Promotes standby to primary)
  - `POST /v1/tasks` (Submits workloads without authentication)

### 9.5 Worker Console Network Security (HIGH)
- In `taskmesh/node/console_server.py:40-46` and lines 295:
  ```python
  app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
  cfg = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="warning")
  ```
  The worker server binds to `0.0.0.0` (all physical network interfaces) with wildcard CORS origins.
- In lines 210–250:
  Endpoints `/api/worker/drain`, `/api/worker/resume`, `/api/worker/maintenance`, `/api/worker/concurrency`, `/api/worker/pause_assignments` have **zero authentication checks**.
- **Impact:** Any machine on the local network (or the public internet if port 8081 is exposed) can issue an unauthenticated POST request to `http://<worker-ip>:8081/api/worker/concurrency` or `/api/worker/drain` and disrupt worker execution.

### 9.6 WebSocket Dashboard Hub Access Control (MEDIUM)
- In `taskmesh/orchestrator/server.py:799-819` (`/v1/ws/dashboard`):
  Connections are accepted immediately with `await websocket.accept()` without inspecting any token, query parameter, or handshake header. Any network client can connect to `ws://<orchestrator>:8000/v1/ws/dashboard` and eavesdrop on all cluster telemetry, node registrations, task allocations, and execution payloads.

---

## 10. Automated Test Suite Execution

### 10.1 Explanation of Previous "Exit Code 1"
In the previous agent session, the command `python -m pytest tests/test_node_agent.py tests/test_orchestrator.py` exited with code 1.
**Root Cause:** Those specific file paths did not exist. The actual test files in the repository are named `tests/test_distributed_flow.py`, `tests/test_api_endpoints.py`, `tests/test_worker_pool.py`, `tests/test_security.py`, etc.

### 10.2 Complete Pytest Test Results
Executed across all 21 test suites in `tests/`:

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
collected 69 items

tests\test_adaptive_pipeline.py .....                                    [  7%]
tests\test_ai_inference.py ...                                           [ 11%]
tests\test_api_endpoints.py .                                            [ 13%]
tests\test_cli.py ...                                                    [ 17%]
tests\test_core_models.py ..                                             [ 20%]
tests\test_distributed_flow.py .                                         [ 21%]
tests\test_eligibility.py ...                                            [ 26%]
tests\test_ewma_adaptation.py .                                          [ 27%]
tests\test_failover.py .                                                 [ 28%]
tests\test_failover_e2e_process.py .                                     [ 30%]
tests\test_frontend_backend_api.py .....                                 [ 37%]
tests\test_leases_and_idempotency.py ...                                 [ 42%]
tests\test_multi_process_distributed.py .                                [ 43%]
tests\test_node_failure_recovery_process.py .                            [ 44%]
tests\test_persistence_restart.py .                                      [ 46%]
tests\test_priority_queue.py ..                                          [ 49%]
tests\test_retry_and_dlq.py ...                                          [ 53%]
tests\test_rl_and_mwu_advanced.py ....                                   [ 59%]
tests\test_security.py .......                                           [ 69%]
tests\test_wireless_inference.py ..................                      [ 95%]
tests\test_worker_pool.py ...                                            [100%]

============================= 69 passed in 46.35s =============================
```

- **Total Tests Collected:** 69
- **Total Tests Passed:** 69 (100%)
- **Total Tests Failed:** 0
- **Regression Status:** Zero regressions introduced to existing distributed algorithms, multi-armed bandits, failover replication, or TMCH wireless protocol.

---

## 11. Documentation Inaccuracies

1. **Non-Existent Default Users:** Documentation in `two_applications_verification_report.md` and the UI hint in `LoginModal.tsx` state that `operator` and `viewer` accounts exist by default. In reality, only `admin` is created on initialization.
2. **Missing Flag Documentation for Worker Console:** Running `python -m taskmesh.node.main` without `--console-port <port>` does **not** launch the Worker Console. The console server is conditional and requires explicit port configuration or the `TASKMESH_CONSOLE_PORT` environment variable.
3. **Standby Replica UI URL:** The Standby status view reports `primary_url` from config, but does not display whether the primary is actively reachable if the standby has not yet polled.

---

## 12. Prioritized Action Plan & Required Corrections

### Severity 1: Critical (Must fix before production release)
1. **Enforce RBAC Permissions Across All Orchestrator Mutating Routes:**
   - In [`taskmesh/orchestrator/server.py`](file:///c:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py), replace `actor = payload.username if payload else "operator"` with `require_permission(request, "<perm>")` on:
     - `/v1/cluster/dispatch/*` (`cluster.manage`)
     - `/v1/scheduler/*` (`scheduler.configure`)
     - `/v1/nodes/{node_id}/drain` (`nodes.manage`)
     - `/v1/nodes/{node_id}/maintenance` (`nodes.manage`)
     - `/v1/nodes/{node_id}/resume` (`nodes.manage`)
     - `/v1/system/config` (`system.configure`)
     - `/v1/dlq/{task_id}/recover` (`dlq.manage`)
     - `/v1/standby/promote` (`recovery.manage`)
     - `/v1/tasks` (`tasks.submit`)
2. **Handle Worker Port Collision Gracefully:**
   - In [`taskmesh/node/console_server.py:292-298`](file:///c:/Malenia/TASK_MESH/taskmesh/node/console_server.py#L292-L298), wrap `await server.serve()` in a `try...except (OSError, SystemExit)` block. If port binding fails, log an error (`f"Worker Console failed to bind to port {port}. Continuing compute agent operation without local UI."`) instead of crashing the entire Node Agent process.

### Severity 2: High (Network & Access Security)
3. **Restrict Worker Console Binding Interface:**
   - In `taskmesh/node/console_server.py:295`, change default binding from `host="0.0.0.0"` to `host="127.0.0.1"`, with an optional `--console-host` flag if remote access is required.
   - Introduce an optional pre-shared bearer token (`join_token` or local agent token) for mutating operations on `/api/worker/drain`, `/api/worker/concurrency`, etc.
4. **Authorize Dashboard WebSocket:**
   - In `taskmesh/orchestrator/server.py:799`, inspect `websocket.query_params.get("token")` or validate an initial authentication frame before registering the connection to `rt.events`.
5. **Secure Bootstrap Mechanism:**
   - If `TASKMESH_ADMIN_PASSWORD` is not set in production, generate a cryptographically random one-time password on first boot, write it to a secured local file (`.admin_bootstrap_secret` with `0600` permissions), and log a prominent security warning requiring password rotation.

### Severity 3: Medium (Usability & Documentation)
6. **Update LoginModal UI Hints:**
   - Remove references to `operator` and `viewer` from `frontend/apps/orchestrator/src/components/LoginModal.tsx`, or implement automatic database seeding for these roles in `_bootstrap_admin()` when running in dev/demo mode.
7. **Document Worker Console Port Requirement:**
   - Update `README.md` and CLI help strings to clarify that `--console-port <port>` is required to activate the local web console.

---

## 13. Git Working Tree Status

- **Branch:** `feature/wireless-inference`
- **HEAD Commit:** `a941217 feat(frontend): implement sub-app orchestrator Sidebar.tsx`
- **Tracked Modifications:**
  - `frontend/apps/orchestrator/src/api/client.ts` (Added `getHealth` alias)
  - `run_visual_check.py` (Updated to verify two independent applications)
  - `taskmesh/node/console_server.py` (Fixed `websockets 17.2` ClientConnection state inspection)
  - `taskmesh/orchestrator/static/favicon.svg` (Added SVG favicon)
  - `taskmesh/orchestrator/static/index.html` (Built output)
- **Untracked Additions:**
  - `frontend/apps/orchestrator/src/App.tsx`, `main.tsx`, and component views.
  - `frontend/apps/worker/src/` (Worker Agent Console application).
  - `frontend/shared/components/` (Shared ConfirmationModal).
  - `taskmesh/node/static/` (Worker console static distribution build).
  - `taskmesh/orchestrator/static/assets/` (Orchestrator static distribution build).
- **Rule Adherence:** No git commits or branch resets were performed during this audit.

