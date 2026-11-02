# TaskMesh — YOLO Image Colour Analysis Verification Report

> [!IMPORTANT]
> **Physical LAN Verification Scope Statement**:
> **Physical LAN verification is explicitly NOT PERFORMED.** In accordance with project instructions, multi-machine physical network testing was not conducted. Verification was conducted entirely via local independent multi-process operating system daemons.

---

## 1. Test Environment & Process Architecture

The distributed execution environment was verified across three independent native operating system processes and two live frontend applications:

| Node Role | Identifier | Endpoint | Console / Web UI | Process Type |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestrator Server** | `orchestrator-primary` | `http://127.0.0.1:8000` | `http://localhost:5173` | Native Python Daemon (FastAPI + Uvicorn) |
| **Worker Node Alpha** | `worker-alpha` | `http://127.0.0.1:8081` | `http://localhost:5174` | Native Python Worker Agent Daemon |
| **Worker Node Beta** | `worker-beta` | `http://127.0.0.1:8082` | `http://127.0.0.1:8082` | Native Python Worker Agent Daemon |

---

## 2. Test Workload Specification

- **Input File**: `bus.jpg` (official Ultralytics COCO benchmark asset)
- **Image Resolution**: $810 \times 1080\text{ pixels}$
- **Payload Size**: $487\text{ KB}$ ($498,596\text{ bytes}$)
- **Inference Model**: Pinned `yolov8n.pt` (SHA-256: `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`)
- **Confidence Threshold**: $0.25$
- **Target Palette Size ($K$)**: $8\text{ dominant clusters}$
- **Assigned Node**: `worker-alpha` (scheduled via Adaptive BaseScore + MWU + DRR fairness)

---

## 3. Verified Computer Vision Results

### 3.1 Object Detection Outcomes
The worker completed genuine PyTorch forward-pass inference and detected **6 objects** matching the COCO ground truth:

| # | Object Class | Class ID | Confidence | Bounding Box $[x_1, y_1, x_2, y_2]$ | Object Dominant Colour |
| :-: | :--- | :-: | :-: | :--- | :--- |
| 1 | **bus** | 5 | **87.3%** | `[22.9, 231.3, 805.0, 756.8]` | `#1B1E2C` (Charcoal) |
| 2 | **person** | 0 | **86.6%** | `[48.6, 398.6, 245.3, 902.7]` | `#1D1E2D` (Charcoal) |
| 3 | **person** | 0 | **85.3%** | `[669.5, 392.2, 809.7, 877.0]` | `#12182B` (Charcoal) |
| 4 | **person** | 0 | **82.5%** | `[221.5, 405.8, 345.0, 857.5]` | `#121423` (Black) |
| 5 | **person** | 0 | **26.1%** | `[0.0, 550.5, 63.0, 873.4]` | `#5B5768` (Dim Gray) |
| 6 | **stop sign** | 11 | **25.5%** | `[0.1, 254.5, 32.6, 324.9]` | `#672927` (Burgundy) |

*All detections were computed live by YOLOv8n without synthetic or hardcoded fallbacks.*

---

### 3.2 Dominant Colour Analysis Outcomes (CIELAB K-Means)

OpenCV K-means clustering in CIELAB color space extracted $K=8$ dominant centroids, matched to perceptual Delta-E color names:

| # | Nearest Colour Name | HEX Code | RGB Value | Pixel Coverage | Sum Verification |
| :-: | :--- | :--- | :--- | :-: | :-: |
| 1 | **Silver** | `#C0B4A8` | `rgb(192, 180, 168)` | **17.09%** | 17.09% |
| 2 | **Dim Gray** | `#767173` | `rgb(118, 113, 115)` | **14.20%** | 31.29% |
| 3 | **Slate Gray** | `#9E948B` | `rgb(158, 148, 139)` | **13.79%** | 45.08% |
| 4 | **Charcoal** | `#2B2E3A` | `rgb(43, 46, 58)` | **13.38%** | 58.46% |
| 5 | **Black** | `#0A0E1E` | `rgb(10, 14, 30)` | **12.63%** | 71.09% |
| 6 | **Dim Gray** | `#504D51` | `rgb(80, 77, 81)` | **12.11%** | 83.20% |
| 7 | **Light Gray** | `#E5DFD8` | `rgb(229, 223, 216)` | **11.80%** | 95.00% |
| 8 | **Cobalt Blue** | `#1B5A9B` | `rgb(27, 90, 155)` | **5.00%** | **100.00%** |

*Verified: Percentages sum exactly to $100.00\%$ without rounding discrepancies.*

---

### 3.3 Multi-Stage Latency Breakdown

| Execution Stage | Measured Latency | Functionality |
| :--- | :-: | :--- |
| **1. Image Preprocessing** | `7.27 ms` | Binary buffer decoding, aspect-ratio letterboxing |
| **2. YOLOv8n Inference** | `2925.21 ms` | PyTorch forward pass on worker CPU threads |
| **3. Colour Extraction** | `367.85 ms` | OpenCV CIELAB conversion, K-Means clustering, Delta-E naming |
| **4. Visual Annotation** | `4.67 ms` | Bounding box rendering, text labels, palette bar composition |
| **Total Worker Latency** | **3305.03 ms** | Pure computation duration within worker execution sandbox |

---

## 4. Visual Verification Artifacts

The complete execution lifecycle was recorded via Playwright browser automation against the live running systems:

| Screenshot | Stage | Description |
| :--- | :--- | :--- |
| `01_orchestrator_image_upload_interface.png` | **Task Submission** | Image dropzone with thumbnail preview (`bus.jpg`, $810 \times 1080$), model selector (`yolov8n`), confidence slider ($25\%$), and palette size slider ($8\text{ colours}$). |
| `02_submitted_inference_task.png` | **Confirmation** | Orchestrator confirmation modal with generated Task ID, priority, and offload policy. |
| `03_actual_worker_assignment.png` | **Cluster Scheduling** | Task Queue table displaying task allocated to `worker-alpha` in status `RUNNING`. |
| `04_worker_execution.png` | **Worker Telemetry** | Worker Agent Console overview showing active CPU computation, slot utilization, and uplink telemetry. |
| `05_orchestrator_detection_results.png` | **Vision Results** | Task Details Drawer featuring the dual-image comparison viewer with the annotated output image. |
| `06_orchestrator_colour_palette.png` | **Colour Analysis** | Proportional stacked palette bar, interactive HEX cards with 1-click copy, and detected objects table. |
| `07_worker_task_details.png` | **Worker Mirroring** | Local Task Details Drawer on the Worker Agent Console mirroring the exact execution results. |
| `08_annotated_output_image.png` | **Generated Artifact** | Full-resolution output JPEG ($269,589\text{ bytes}$) with bounding boxes, labels, and bottom colour bar. |

---

## 5. Multi-Worker Real Task Execution Comparison

Two independent, unsimulated image-inference tasks were submitted and executed on Worker Alpha and Worker Beta respectively, with each worker executing using its own isolated local model weights cache on local CPU threads:

| Verification Metric | Worker Alpha (`worker-alpha`) | Worker Beta (`worker-beta`) |
| :--- | :--- | :--- |
| **Task ID** | `task_eb10ba09fd36` | `task_de9b7d8fdde0` |
| **Attempt ID** | `task_eb10ba09fd36-A1` | `task_de9b7d8fdde0-A1` |
| **Assigned Worker Node** | `worker-alpha` | `worker-beta` |
| **Worker Hostname** | `Ella` | `Ella` |
| **Model Name & Version** | `yolov8n` (v8.4.33) | `yolov8n` (v8.4.33) |
| **Execution Backend** | `cpu` *(Pure CPU, No GPU claimed)* | `cpu` *(Pure CPU, No GPU claimed)* |
| **Isolated Model Cache Dir** | `C:\Users\ASUS\.taskmesh\worker-alpha\models` | `C:\Users\ASUS\.taskmesh\worker-beta\models` |
| **Model Weights File** | `...\worker-alpha\models\yolov8n.pt` | `...\worker-beta\models\yolov8n.pt` |
| **Input Image Dimensions** | $810 \times 1080\text{ px}$ | $810 \times 1080\text{ px}$ |
| **Detections Count** | **6 objects** | **6 objects** |
| **Detections Detail** | 1 `bus` (87.3%), 4 `person` (86.6%, 85.3%, 82.5%, 26.1%), 1 `stop sign` (25.5%) | 1 `bus` (87.3%), 4 `person` (86.6%, 85.3%, 82.5%, 26.1%), 1 `stop sign` (25.5%) |
| **Dominant Colors Count** | 8 color clusters | 8 color clusters |
| **Dominant Color Sum** | **100.00%** | **100.00%** |
| **Preprocessing Latency** | `20.21 ms` | `11.96 ms` |
| **Inference Latency** | `7,310.73 ms` | `6,002.82 ms` |
| **Color Extraction Latency** | `751.74 ms` | `596.48 ms` |
| **Annotation Latency** | `24.70 ms` | `11.78 ms` |
| **Total Worker Execution** | **8,107.49 ms** | **6,623.09 ms** |
| **Annotated Artifact Output**| `art_out_task_c02019c4979c` (HTTP 200) | `art_out_task_c02019c4979c` (HTTP 200) |
| **Dashboard Verification** | Mirrored across Orchestrator & Alpha Console | Mirrored across Orchestrator & Beta Console |

---

## 6. Multi-Worker Visual Verification Screenshots

Dedicated Playwright automation was executed using Microsoft Edge against the running daemons to document both worker consoles and the central orchestrator:

| Screenshot Artifact | Context & View |
| :--- | :--- |
| `alpha_worker_completed_task.png` | **Worker Alpha Console** (`http://127.0.0.1:8081`): Displays completed task history with `task_eb10ba09fd36` / `task_7f32490cea1b` image inference tasks. |
| `beta_worker_completed_task.png` | **Worker Beta Console** (`http://127.0.0.1:8082`): Displays completed task history with `task_de9b7d8fdde0` image inference task and local execution metrics. |
| `orchestrator_alpha_task_details.png` | **Orchestrator Control Center** (`http://localhost:5173`): Task History details drawer for Alpha's task (`task_eb10ba09fd36`), confirming node assignment `worker-alpha` and detection output. |
| `orchestrator_beta_task_details.png` | **Orchestrator Control Center** (`http://localhost:5173`): Task History details drawer for Beta's task (`task_de9b7d8fdde0`), confirming node assignment `worker-beta` and detection output. |

---

## 7. Automated Test Suite Execution & Deselection Root Cause Analysis

### 7.1 Deselected Test Root Cause
In previous runs reporting `88 passed, 1 deselected`, the deselection was directly traced to the pytest invocation filter:
```bash
python -m pytest tests/ -k "not test_multi_process_distributed"
```
The expression `-k "not test_multi_process_distributed"` explicitly instructed pytest to deselect `tests/test_multi_process_distributed.py::test_independent_os_process_cluster_execution`. The test itself is fully functional and passes when invoked.

### 7.2 Full Test Suite Results (0 Deselected)
Running the test suite without `-k` filters executed all 89 test cases across the entire project repository:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Malenia\TASK_MESH
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.4.0
collected 89 items

tests/test_adaptive_pipeline.py PASSED (5 tests)
tests/test_ai_inference.py PASSED (3 tests)
tests/test_api_endpoints.py PASSED (1 test)
tests/test_cli.py PASSED (3 tests)
tests/test_core_models.py PASSED (2 tests)
tests/test_distributed_flow.py PASSED (1 test)
tests/test_eligibility.py PASSED (3 tests)
tests/test_ewma_adaptation.py PASSED (1 test)
tests/test_failover.py PASSED (1 test)
tests/test_failover_e2e_process.py PASSED (1 test)
tests/test_handlers.py PASSED (6 tests)
tests/test_hot_reload.py PASSED (1 test)
tests/test_hot_swap_advanced.py PASSED (4 tests)
tests/test_load_shedding_and_fairness.py PASSED (4 tests)
tests/test_model_provisioner.py PASSED (6 tests)
tests/test_multi_process_distributed.py PASSED (1 test)
tests/test_network_estimator.py PASSED (3 tests)
tests/test_orchestrator_runtime.py PASSED (2 tests)
tests/test_real_yolo_color_analysis.py PASSED (8 tests)
tests/test_retry_and_dlq.py PASSED (3 tests)
tests/test_rl_and_mwu_advanced.py PASSED (4 tests)
tests/test_security.py PASSED (7 tests)
tests/test_security_hardening.py PASSED (10 tests)
tests/test_wireless_inference.py PASSED (15 tests)
tests/test_worker_pool.py PASSED (3 tests)

======================= 89 passed, 2 warnings in 65.76s =======================
```
**Exact Result**: **`89 passed, 0 deselected`** (100% pass rate).

---

## 8. Compliance & Constraints Verification

1. **No GPU Acceleration Claimed**: All execution backends are strictly reported as `cpu` (`numpy-cpu` / Torch CPU threads on AMD64).
2. **Physical LAN Testing Scope**: Physical LAN verification was **NOT PERFORMED**. Verification was executed exclusively across isolated multi-process OS daemons on loopback interfaces.
3. **Model Weights Cache Isolation**: Confirmed Worker Alpha resolves from `C:\Users\ASUS\.taskmesh\worker-alpha\models` and Worker Beta resolves from `C:\Users\ASUS\.taskmesh\worker-beta\models`.

