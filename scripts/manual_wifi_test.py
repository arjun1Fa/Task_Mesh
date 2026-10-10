#!/usr/bin/env python3
"""TASKMESH PHYSICAL MULTI-MACHINE WI-FI TEST SCRIPT
===================================================

This script orchestrates and verifies a REAL physical wireless AI inference
offloading experiment between TWO machines connected to the same Wi-Fi/LAN network.

ARCHITECTURE FOR TEST:
Machine A (Originating Device):
  - Runs TaskMesh Orchestrator bound to 0.0.0.0:8000
  - Submits an image inference task with real binary payload (JPEG/PNG)
  - Uses either CLI or this script

Machine B (Compute/GPU Node):
  - Runs TaskMesh Node Agent connected to Machine A's Wi-Fi IP:
    taskmesh node --orchestrator ws://<MACHINE_A_IP>:8000
  - Receives binary frames over WebSocket
  - Runs local YOLO / OpenCV inference
  - Returns structured detections (labels, bounding boxes, inference time)

SAFETY & TRUTH NOTICE:
This script performs real network I/O over HTTP and WebSockets.
Do NOT run this on localhost if claiming a physical Wi-Fi test!
"""

import argparse
import io
import json
import os
import socket
import sys
import time
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install via: pip install httpx")
    sys.exit(1)


def detect_local_lan_ip() -> str:
    """Detects active LAN IP on the local network interface."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_synthetic_test_image(output_path: str = "wifi_test_image.jpg") -> str:
    """Generates a synthetic image with geometric patterns if no image is supplied."""
    try:
        import numpy as np
        import cv2

        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Blue gradient background
        for y in range(480):
            img[y, :, 0] = int(255 * (y / 480))
            img[y, :, 1] = int(120 * (1 - y / 480))
            img[y, :, 2] = 200

        # Draw simulated bounding boxes & text
        cv2.rectangle(img, (100, 100), (300, 380), (0, 255, 0), 3)
        cv2.putText(img, "TEST OBJECT A", (105, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.rectangle(img, (350, 150), (550, 420), (0, 165, 255), 3)
        cv2.putText(img, "TEST OBJECT B", (355, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        cv2.imwrite(output_path, img)
        return output_path
    except ImportError:
        # Fallback to minimal valid JPEG header + data if opencv/numpy missing
        dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x10\x00\x10\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
        with open(output_path, "wb") as f:
            f.write(dummy_jpeg)
        return output_path


def run_physical_test(orchestrator_url: str, image_path: str, poll_timeout_s: float = 30.0) -> None:
    lan_ip = detect_local_lan_ip()
    print("=" * 70)
    print("TASKMESH PHYSICAL MULTI-MACHINE WI-FI TEST")
    print("=" * 70)
    print(f"Machine Local LAN IP:        {lan_ip}")
    print(f"Target Orchestrator URL:     {orchestrator_url}")
    print(f"Input Image Path:            {image_path}")

    if not os.path.exists(image_path):
        print(f"Generating synthetic test image at {image_path}...")
        generate_synthetic_test_image(image_path)

    file_size_bytes = os.path.getsize(image_path)
    file_size_kb = file_size_bytes / 1024
    print(f"Image File Size:             {file_size_kb:.2f} KB ({file_size_bytes} bytes)")
    print("-" * 70)

    client = httpx.Client(base_url=orchestrator_url, timeout=10.0)

    # 1. Health & Cluster Check
    print("[1/5] Verifying Orchestrator and Connected Nodes...")
    try:
        health_resp = client.get("/v1/health")
        if health_resp.status_code != 200:
            print(f"ERROR: Orchestrator health check failed with status {health_resp.status_code}")
            return
        health = health_resp.json()
        print(f"  -> Orchestrator: {health.get('status')} (leader: {health.get('is_leader')})")

        nodes_resp = client.get("/v1/nodes")
        nodes = nodes_resp.json() if nodes_resp.status_code == 200 else []
        print(f"  -> Discovered {len(nodes)} active node(s):")
        for n in nodes:
            caps = n.get("capabilities", {})
            print(f"     * Node: {n.get('id')} | IP: {n.get('lan_ip')} | Local: {caps.get('is_local')} | GPU: {caps.get('has_gpu')} ({caps.get('gpu_name')})")

        if len(nodes) == 0:
            print("\nWARNING: No nodes are currently connected to the orchestrator.")
            print("To start a remote node on Machine B:")
            print(f"  taskmesh node --orchestrator ws://{lan_ip}:8000\n")
            cont = input("Continue anyway to submit task? (y/N): ").strip().lower()
            if cont != "y":
                return
    except Exception as e:
        print(f"Connection error to {orchestrator_url}: {e}")
        return

    # 2. Submit Binary Image Task
    print("\n[2/5] Submitting Binary Task to POST /v1/tasks/binary...")
    start_t = time.perf_counter()
    with open(image_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": (os.path.basename(image_path), file_bytes, "image/jpeg")}
    data = {
        "task_type": "image_inference",
        "offload_policy": "wireless_allowed",
        "priority": 5,
        "requires_gpu": False,
    }

    resp = client.post("/v1/tasks/binary", data=data, files=files)
    submit_duration_ms = (time.perf_counter() - start_t) * 1000

    if resp.status_code != 200:
        print(f"ERROR submitting task: {resp.status_code} - {resp.text}")
        return

    task_data = resp.json()
    task_id = task_data["id"]
    print(f"  -> Task submitted successfully in {submit_duration_ms:.2f}ms!")
    print(f"  -> Task ID:       {task_id}")
    print(f"  -> Status:        {task_data.get('status')}")
    print(f"  -> Policy:        {task_data.get('offload_policy')}")
    if "binary_meta" in task_data and task_data["binary_meta"]:
        print(f"  -> SHA-256 Hash:  {task_data['binary_meta'].get('checksum_sha256')}")

    # 3. Poll for Completion
    print(f"\n[3/5] Polling for completion (timeout={poll_timeout_s}s)...")
    poll_start = time.perf_counter()
    completed_task = None
    while time.perf_counter() - poll_start < poll_timeout_s:
        t_resp = client.get(f"/v1/tasks/{task_id}")
        if t_resp.status_code == 200:
            t_info = t_resp.json()
            st = t_info.get("status")
            print(f"  [{time.perf_counter() - poll_start:.1f}s] Status: {st} (assigned: {t_info.get('assigned_node_id')})")
            if st in ("completed", "failed", "dlq"):
                completed_task = t_info
                break
        time.sleep(1.0)

    total_e2e_ms = (time.perf_counter() - start_t) * 1000

    if not completed_task:
        print(f"\nTIMEOUT: Task {task_id} did not finish within {poll_timeout_s}s.")
        return

    # 4. Display Results and Telemetry
    print("\n[4/5] Inference Results Received:")
    if completed_task.get("status") == "completed":
        result = completed_task.get("result", {})
        print(json.dumps(result, indent=2))
    else:
        print(f"Task finished with status: {completed_task.get('status')}")
        print(f"Error: {completed_task.get('error')}")

    # 5. Telemetry & Decision Explainability
    print("\n[5/5] TELEMETRY & SCHEDULING EXPLAINABILITY")
    print("=" * 70)
    print(f"Selected Node:           {completed_task.get('assigned_node_id')}")
    print(f"End-to-End Latency:      {total_e2e_ms:.2f} ms")
    if completed_task.get("result") and isinstance(completed_task["result"], dict):
        inf_ms = completed_task["result"].get("inference_time_ms")
        if inf_ms is not None:
            print(f"Remote Inference Time:   {inf_ms:.2f} ms")
        dets = completed_task["result"].get("detections", [])
        print(f"Total Detections Found:  {len(dets)}")
        for d in dets[:5]:
            print(f"   - Class: {d.get('class')}, Confidence: {d.get('confidence'):.2f}, Box: {d.get('bbox')}")
    print("=" * 70)
    print("PHYSICAL TEST EXECUTION COMPLETE.")


def main() -> None:
    parser = argparse.ArgumentParser(description="TaskMesh Physical Wi-Fi Inference Offload Test")
    parser.add_argument("--orchestrator", type=str, default="http://127.0.0.1:8000", help="HTTP URL of Orchestrator")
    parser.add_argument("--image", type=str, default="wifi_test_image.jpg", help="Path to input test image")
    parser.add_argument("--timeout", type=float, default=30.0, help="Polling timeout in seconds")
    args = parser.parse_args()

    run_physical_test(args.orchestrator, args.image, args.timeout)


if __name__ == "__main__":
    main()
