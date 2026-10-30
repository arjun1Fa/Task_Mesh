# TaskMesh — Technology Stack

## 1. Technology Inventory

TaskMesh prioritizes a lightweight, dependency-conscious architecture. Core orchestration requires only Python standard libraries, FastAPI, Uvicorn, Pydantic, WebSockets, psutil, and NumPy. Heavy machine learning frameworks (`torch`, `ultralytics`, `cv2`) are isolated into an optional `[ai]` dependency group.

---

## 2. Core Technologies

### 2.1 Python 3.11+ / 3.14
- **What It Is**: The primary programming language and runtime environment.
- **Why Selected**: Rapid prototyping, rich asynchronous networking support (`asyncio`), native cross-platform system profiling, and universal adoption across the AI/ML ecosystem.
- **Where Used**: Entire repository.
- **Essential vs. Replaceable**: **Essential**. The core domain, async loops, and models depend directly on Python 3.11+ language features.

### 2.2 FastAPI & Starlette
- **What It Is**: Modern, high-performance web framework for building APIs with Python.
- **Why Selected**: Automatic OpenAPI/Swagger documentation, native ASGI asynchronous support, built-in WebSocket endpoints, and seamless integration with Pydantic v2.
- **Where Used**: [`taskmesh/orchestrator/server.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py).
- **Essential vs. Replaceable**: **Replaceable** (could theoretically be replaced by raw Starlette, Sanic, or aiohttp, but FastAPI provides first-class developer experience and automatic docs).

### 2.3 Uvicorn
- **What It Is**: Lightning-fast ASGI web server implementation for Python.
- **Why Selected**: Industry-standard, production-ready server for hosting FastAPI applications.
- **Where Used**: [`taskmesh/orchestrator/main.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/main.py).
- **Essential vs. Replaceable**: **Replaceable** (Hypercorn or Granian could be substituted).

### 2.4 Pydantic v2
- **What It Is**: Data validation and settings management using Python type annotations.
- **Why Selected**: Rust-backed validation core (`pydantic-core`) ensures high parsing performance, deterministic JSON schema serialization, and strict runtime type safety.
- **Where Used**:
  - [`taskmesh/core/models.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/models.py)
  - [`taskmesh/core/config.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/config.py)
  - [`taskmesh/protocol/messages.py`](file:///C:/Malenia/TASK_MESH/taskmesh/protocol/messages.py)
  - [`taskmesh/scheduler/decision.py`](file:///C:/Malenia/TASK_MESH/taskmesh/scheduler/decision.py)
- **Essential vs. Replaceable**: **Essential**. The protocol contracts and domain validation rely directly on Pydantic v2 schemas.

### 2.5 WebSockets (`websockets` library)
- **What It Is**: Library for building WebSocket servers and clients in Python.
- **Why Selected**: Full-duplex persistent TCP connections, low protocol overhead compared to HTTP/REST polling, support for interleaved text and binary frames.
- **Where Used**:
  - Server: [`taskmesh/orchestrator/server.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/server.py)
  - Client: [`taskmesh/node/agent.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/agent.py)
- **Essential vs. Replaceable**: **Essential**. The distributed communication fabric is built on WebSockets.

### 2.6 `psutil`
- **What It Is**: Cross-platform process and system monitoring library.
- **Why Selected**: Provides accurate, low-overhead CPU core counts, frequency, memory capacity, and real-time utilization percentages on Windows, Linux, and macOS.
- **Where Used**: [`taskmesh/node/hardware.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/hardware.py).
- **Essential vs. Replaceable**: **Essential**. Required for dynamic hardware profiling and node health telemetry.

### 2.7 NumPy
- **What It Is**: Fundamental library for scientific computing in Python.
- **Why Selected**: Vectorized mathematical operations for DRR quantum calculation, coefficient of variation statistics, and fast in-memory array manipulation.
- **Where Used**:
  - [`taskmesh/fairness/drr.py`](file:///C:/Malenia/TASK_MESH/taskmesh/fairness/drr.py)
  - [`taskmesh/learning/mwu.py`](file:///C:/Malenia/TASK_MESH/taskmesh/learning/mwu.py)
  - [`taskmesh/handlers/ai_inference.py`](file:///C:/Malenia/TASK_MESH/taskmesh/handlers/ai_inference.py)
- **Essential vs. Replaceable**: **Replaceable** (math formulas could be rewritten in pure Python `math`, but NumPy provides cleaner numerical operations).

### 2.8 SQLite (`sqlite3`)
- **What It Is**: Self-contained, serverless, zero-configuration SQL database engine built into the Python standard library.
- **Why Selected**: Zero external service dependencies; delivers crash-resilient local persistence for tasks and leases out of the box.
- **Where Used**: [`taskmesh/persistence/repositories.py`](file:///C:/Malenia/TASK_MESH/taskmesh/persistence/repositories.py).
- **Essential vs. Replaceable**: **Replaceable**. The codebase uses the repository pattern (`TaskRepository` protocol). A PostgreSQL or Redis repository can be implemented without changing orchestrator domain logic.

---

## 3. Optional Machine Learning & Vision Stack (`[ai]`)

### 3.1 PyTorch (`torch`)
- **What It Is**: Open-source machine learning and deep learning framework.
- **Why Selected**: CUDA GPU detection, GPU device memory queries (`torch.cuda.memory_allocated`), and baseline neural tensor passes.
- **Where Used**:
  - Hardware Profiler: [`taskmesh/node/hardware.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/hardware.py)
  - Fallback Vision Handler: [`taskmesh/handlers/ai_inference.py`](file:///C:/Malenia/TASK_MESH/taskmesh/handlers/ai_inference.py)
- **Essential vs. Replaceable**: **Optional**. If PyTorch is absent, TaskMesh gracefully falls back to CPU/NumPy profiling.

### 3.2 Ultralytics YOLOv8 (`ultralytics`)
- **What It Is**: Leading real-time object detection and computer vision framework.
- **Why Selected**: Provides realistic end-to-end vision inference benchmarking on real JPEG camera images.
- **Where Used**: [`taskmesh/handlers/ai_inference.py`](file:///C:/Malenia/TASK_MESH/taskmesh/handlers/ai_inference.py).
- **Essential vs. Replaceable**: **Optional**. Handlers gracefully fall back to simulated structured detections if Ultralytics is not installed.

### 3.3 OpenCV (`cv2`)
- **What It Is**: Open-source computer vision and image processing library.
- **Why Selected**: Rapid decoding of raw binary JPEG bytes into memory arrays (`cv2.imdecode`) without disk I/O.
- **Where Used**: [`taskmesh/handlers/ai_inference.py`](file:///C:/Malenia/TASK_MESH/taskmesh/handlers/ai_inference.py), [`scripts/manual_wifi_test.py`](file:///C:/Malenia/TASK_MESH/scripts/manual_wifi_test.py).
- **Essential vs. Replaceable**: **Optional**.

---

## 4. Client & Operations Stack

### 4.1 HTTPX
- **What It Is**: Full-featured HTTP client library supporting async and sync I/O.
- **Why Selected**: Powers the CLI (`taskmeshctl`), Standby snapshot polling, and integration test clients.
- **Where Used**: [`taskmesh/cli/main.py`](file:///C:/Malenia/TASK_MESH/taskmesh/cli/main.py), [`taskmesh/orchestrator/runtime.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/runtime.py).

### 4.2 Frontend Web Dashboard (Vanilla HTML5 / CSS3 / JavaScript)
- **What It Is**: Embedded web management dashboard.
- **Why Selected**: Zero build step (no Node.js, Webpack, or npm required). Easily modified and served directly by FastAPI.
- **Where Used**:
  - HTML: [`taskmesh/orchestrator/static/index.html`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/static/index.html)
  - CSS: [`taskmesh/orchestrator/static/css/style.css`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/static/css/style.css)
  - JS: [`taskmesh/orchestrator/static/js/app.js`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/static/js/app.js)

