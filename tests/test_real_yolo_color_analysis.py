"""Comprehensive Automated Regression Suite for Real YOLO Object Detection and OpenCV Colour Analysis."""

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict
import cv2
import numpy as np
import pytest
import ultralytics
from httpx import ASGITransport, AsyncClient

from taskmesh.core.enums import NodeStatus, TaskStatus
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task, TaskCreate
from taskmesh.handlers.ai_inference import (
    estimate_object_color,
    extract_dominant_colors,
    find_nearest_color_name,
    image_inference_handler,
)
from taskmesh.node.agent import NodeAgent
from taskmesh.node.model_provisioner import ModelProvisioner, get_model_provisioner
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.orchestrator.server import create_app
from taskmesh.scheduler.base import filter_eligible_nodes


@pytest.fixture
def real_bus_image_bytes() -> bytes:
    """Loads the official real test image from Ultralytics package assets."""
    bus_path = os.path.join(os.path.dirname(ultralytics.__file__), "assets", "bus.jpg")
    assert os.path.exists(bus_path), f"Sample image {bus_path} not found"
    with open(bus_path, "rb") as f:
        return f.read()


@pytest.fixture
def temp_cache_dir():
    d = tempfile.mkdtemp(prefix="taskmesh_yolo_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# =====================================================================
# 1. Unit Tests for Computer Vision & Colour Engine
# =====================================================================

def test_color_naming_and_palette_sum(real_bus_image_bytes):
    """Verifies that dominant color clustering on a real image produces ~100% sum and valid named colors."""
    nparr = np.frombuffer(real_bus_image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert img is not None

    palette, centers = extract_dominant_colors(img, k=8)
    assert len(palette) == 8
    total_pct = sum(c["percentage"] for c in palette)
    assert 99.8 <= total_pct <= 100.2, f"Total percentage should sum to ~100%, got {total_pct}"

    for c in palette:
        assert "name" in c and c["name"] != "Unknown"
        assert "hex" in c and c["hex"].startswith("#") and len(c["hex"]) == 7
        assert len(c["rgb"]) == 3
        assert 0 <= c["percentage"] <= 100.0
        assert c["pixel_count"] > 0


def test_synthetic_two_color_split():
    """Verifies color extraction on a synthetic image containing exactly 50% pure blue and 50% pure red."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :50] = (255, 0, 0)    # Blue in BGR
    img[:, 50:] = (0, 0, 255)    # Red in BGR

    palette, _ = extract_dominant_colors(img, k=3)
    names = [c["name"] for c in palette[:2]]
    # Must identify blue and red/scarlet/crimson tones
    assert any("Blue" in n for n in names)
    assert any("Red" in n or "Crimson" in n or "Scarlet" in n for n in names)


def test_per_object_color_estimation(real_bus_image_bytes):
    """Verifies that bounding-box crop color estimation identifies object-region color."""
    nparr = np.frombuffer(real_bus_image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Bus region roughly: [20, 230, 800, 750]
    bus_color = estimate_object_color(img, [20.0, 230.0, 800.0, 750.0])
    assert "hex" in bus_color
    assert "rgb" in bus_color
    assert "name" in bus_color
    assert bus_color["approximation"] == "bounding_box_crop"


# =====================================================================
# 2. Model Provisioner & Capability Tests
# =====================================================================

def test_model_provisioner_lifecycle(temp_cache_dir):
    """Verifies model provisioner checks cache, verifies weights, and detects backend."""
    prov = ModelProvisioner(cache_dir=temp_cache_dir)
    assert not prov.is_model_cached("yolov8n")

    # Provision model
    path = prov.ensure_model("yolov8n")
    assert os.path.exists(path)
    assert prov.is_model_cached("yolov8n")

    # Verify and load
    ready, model, info = prov.verify_and_load("yolov8n")
    assert ready is True
    assert model is not None
    assert info["available"] is True
    assert info["backend"] in ("cpu", "cuda:0")
    assert info["version"] == "8.4.33"


def test_scheduler_model_capability_filtering():
    """Verifies scheduler filters out nodes that lack the requested YOLO model."""
    node_ready = NodeProfile(
        id="worker-ai-ready",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            supported_handlers=["image_inference"],
            supported_models=["yolov8n"],
            model_readiness={"yolov8n": {"available": True}},
        ),
    )
    node_unready = NodeProfile(
        id="worker-ai-unready",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            supported_handlers=["image_inference"],
            supported_models=[],
            model_readiness={"yolov8n": {"available": False, "error": "weights missing"}},
        ),
    )
    node_cpu_only = NodeProfile(
        id="worker-cpu-only",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            supported_handlers=["cpu_test"],
        ),
    )

    task_yolo = Task(task_type="image_inference", payload={"model": "yolov8n"})
    candidates = [node_ready, node_unready, node_cpu_only]

    eligible = filter_eligible_nodes(task_yolo, candidates)
    assert len(eligible) == 1
    assert eligible[0].id == "worker-ai-ready"


# =====================================================================
# 3. Direct Handler Verification on Real Image
# =====================================================================

def test_image_inference_handler_real_execution(real_bus_image_bytes):
    """Executes the complete real computer vision handler on bus.jpg."""
    payload = {
        "model": "yolov8n",
        "confidence_threshold": 0.25,
        "palette_size": 8,
    }
    result = image_inference_handler(payload, binary_payload=real_bus_image_bytes)

    assert result["model"]["name"] == "yolov8n"
    assert result["model"]["backend"] in ("cpu", "cuda:0")
    assert result["image_dimensions"] == [810, 1080]
    assert result["detections_count"] >= 3, "Should detect at least bus and persons"

    # Verify detected objects contain classes, confidences, boxes, and object colors
    detected_classes = [d["class"] for d in result["detections"]]
    assert "bus" in detected_classes
    assert "person" in detected_classes

    for d in result["detections"]:
        assert 0.0 <= d["confidence"] <= 1.0
        assert len(d["bbox"]) == 4
        assert "object_color" in d
        assert "name" in d["object_color"]
        assert "hex" in d["object_color"]

    # Verify dominant colors
    assert len(result["dominant_colors"]) == 8
    total_pct = sum(c["percentage"] for c in result["dominant_colors"])
    assert 99.8 <= total_pct <= 100.2

    # Verify timings
    timings = result["timings"]
    assert timings["preprocessing_ms"] >= 0.0
    assert timings["inference_ms"] > 0.0
    assert timings["color_extraction_ms"] > 0.0
    assert timings["total_execution_ms"] > 0.0

    # Verify annotated image bytes
    ann_bytes = result.get("_annotated_image_bytes")
    assert ann_bytes is not None and len(ann_bytes) > 10000
    assert ann_bytes.startswith(b"\xff\xd8")  # JPEG header


def test_corrupted_image_handling():
    """Verifies that submitting corrupted bytes raises an explicit ValueError."""
    corrupted_data = b"NOT_A_REAL_IMAGE_DATA_123456789"
    with pytest.raises(ValueError, match="Invalid or corrupted binary image payload"):
        image_inference_handler({"model": "yolov8n"}, binary_payload=corrupted_data)


# =====================================================================
# 4. End-to-End Orchestrator + API Validation
# =====================================================================

@pytest.mark.asyncio
async def test_api_binary_task_submission_and_artifacts(real_bus_image_bytes):
    """Tests POST /v1/tasks/binary, input validation, and artifact endpoints."""
    from taskmesh.core.config import OrchestratorConfig
    from taskmesh.persistence.repositories import MemoryTaskRepository

    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig(heartbeat_interval_seconds=1.0)
    rt = OrchestratorRuntime(repository=repo, config=cfg)
    app = create_app(runtime=rt)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login as admin
        login_resp = await client.post("/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Submit real image task via multipart/form-data
        files = {"file": ("bus.jpg", real_bus_image_bytes, "image/jpeg")}
        data = {"model": "yolov8n", "priority": "7", "confidence_threshold": "0.3", "palette_size": "8"}
        res = await client.post("/v1/tasks/binary", files=files, data=data, headers=headers)
        assert res.status_code == 201, res.text
        task = res.json()
        task_id = task["id"]
        assert task["task_type"] == "image_inference"
        assert task["priority"] == 7
        assert task["binary_meta"] is not None
        assert task["binary_meta"]["payload_size_bytes"] == len(real_bus_image_bytes)

        # 3. Retrieve input image artifact
        input_img_resp = await client.get(f"/v1/tasks/{task_id}/input-image", headers=headers)
        assert input_img_resp.status_code == 200
        assert len(input_img_resp.content) == len(real_bus_image_bytes)
        assert hashlib.sha256(input_img_resp.content).hexdigest() == hashlib.sha256(real_bus_image_bytes).hexdigest()

        # 4. Upload annotated output image artifact (simulating worker response)
        annotated_test_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"X" * 1024
        art_upload_resp = await client.post(
            f"/v1/tasks/{task_id}/artifacts/annotated-image",
            content=annotated_test_bytes,
            headers={"X-Node-Token": rt.config.join_token, "Content-Type": "image/jpeg"},
        )
        assert art_upload_resp.status_code == 200

        # 5. Retrieve annotated output image artifact
        ann_resp = await client.get(f"/v1/tasks/{task_id}/annotated-image", headers=headers)
        assert ann_resp.status_code == 200
        assert ann_resp.content == annotated_test_bytes

        # 6. Retrieve generic artifact endpoint
        art_id = f"art_out_{task_id}"
        art_resp = await client.get(f"/v1/artifacts/{art_id}", headers=headers)
        assert art_resp.status_code == 200
        assert art_resp.content == annotated_test_bytes

        # 7. Test invalid image rejection
        bad_files = {"file": ("corrupt.jpg", b"corrupted_garbage_bytes", "image/jpeg")}
        bad_res = await client.post("/v1/tasks/binary", files=bad_files, headers=headers)
        assert bad_res.status_code == 400
        assert "Image validation failed" in bad_res.json()["detail"]
