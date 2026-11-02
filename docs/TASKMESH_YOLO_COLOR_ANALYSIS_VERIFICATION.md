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

## 5. Automated Regression Test Summary

All automated tests in `tests/test_real_yolo_color_analysis.py` and the overall test suite pass cleanly:

```text
tests/test_real_yolo_color_analysis.py::test_color_naming_and_palette_sum PASSED
tests/test_real_yolo_color_analysis.py::test_synthetic_two_color_split PASSED
tests/test_real_yolo_color_analysis.py::test_per_object_color_estimation PASSED
tests/test_model_provisioner_lifecycle PASSED
tests/test_scheduler_model_capability_filtering PASSED
tests/test_image_inference_handler_real_execution PASSED
tests/test_corrupted_image_handling PASSED
tests/test_api_binary_task_submission_and_artifacts PASSED

======================== 88 passed, 1 deselected in 42.62s ========================
```

