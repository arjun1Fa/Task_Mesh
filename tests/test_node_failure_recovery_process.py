"""Integration test verifying node failure and automated task recovery with real OS processes."""

import os
import subprocess
import sys
import tempfile
import time
import httpx
import pytest


@pytest.mark.asyncio
async def test_node_process_kill_and_recovery():
    """Validates real node failure recovery:
    1. Orchestrator + 2 Node Agent OS processes
    2. Task dispatched to Node A
    3. Node A OS process is killed (SIGKILL / kill())
    4. Heartbeat timeout triggers OFFLINE
    5. Orchestrator recovers task and reassigns to Node B
    6. Task completes on Node B
    """
    python_bin = sys.executable
    port = 8220
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    processes = []

    try:
        # 1. Start Orchestrator with fast heartbeat timeout
        orch_cmd = [
            python_bin, "-m", "taskmesh.orchestrator.main",
            "--port", str(port),
            "--db", db_path,
            "--heartbeat-interval", "0.2",
            "--node-timeout", "0.6",
            "--lease-seconds", "3.0",
        ]
        p_orch = subprocess.Popen(orch_cmd)
        processes.append(("Orchestrator", p_orch))

        # Wait for orchestrator
        async with httpx.AsyncClient(timeout=2.0) as client:
            ready = False
            for _ in range(25):
                try:
                    resp = await client.get(f"http://127.0.0.1:{port}/v1/cluster/health")
                    if resp.status_code == 200:
                        ready = True
                        break
                except Exception:
                    time.sleep(0.2)
            assert ready

        # 2. Start doomed node process
        ws_url = f"ws://127.0.0.1:{port}/v1/ws/nodes"
        p_doomed = subprocess.Popen([
            python_bin, "-m", "taskmesh.node.main",
            "--node-id", "node-doomed",
            "--url", ws_url,
            "--heartbeat-interval", "0.2",
        ])
        processes.append(("node-doomed", p_doomed))

        # Wait for doomed node to register
        async with httpx.AsyncClient(timeout=2.0) as client:
            for _ in range(20):
                resp = await client.get(f"http://127.0.0.1:{port}/v1/nodes/node-doomed")
                if resp.status_code == 200:
                    break
                time.sleep(0.2)

        # 3. Submit long sleep task (sleep 4s)
        async with httpx.AsyncClient(timeout=5.0) as client:
            submit_resp = await client.post(
                f"http://127.0.0.1:{port}/v1/tasks",
                json={
                    "task_type": "sleep",
                    "payload": {"duration": 4.0},
                    "priority": 10,
                },
            )
            assert submit_resp.status_code == 201
            task_id = submit_resp.json()["id"]

            # Wait until task is dispatched and running on node-doomed
            for _ in range(20):
                t_resp = await client.get(f"http://127.0.0.1:{port}/v1/tasks/{task_id}")
                if t_resp.status_code == 200:
                    data = t_resp.json()
                    if data.get("assigned_node_id") == "node-doomed" and data.get("status") == "running":
                        break
                time.sleep(0.2)

            # 4. Start survivor node process
            p_survivor = subprocess.Popen([
                python_bin, "-m", "taskmesh.node.main",
                "--node-id", "node-survivor",
                "--url", ws_url,
                "--heartbeat-interval", "0.2",
            ])
            processes.append(("node-survivor", p_survivor))

            # Wait for survivor node to register
            for _ in range(20):
                resp = await client.get(f"http://127.0.0.1:{port}/v1/nodes/node-survivor")
                if resp.status_code == 200:
                    break
                time.sleep(0.2)

            # 5. KILL doomed node process abruptly!
            p_doomed.kill()
            p_doomed.wait()

            # 6. Wait for heartbeat timeout detection and reassignment to node-survivor
            reassigned_and_completed = False
            for _ in range(40):
                t_resp = await client.get(f"http://127.0.0.1:{port}/v1/tasks/{task_id}")
                if t_resp.status_code == 200:
                    data = t_resp.json()
                    if data.get("status") == "completed":
                        assert data.get("assigned_node_id") == "node-survivor"
                        assert data["result"]["node_id"] == "node-survivor"
                        reassigned_and_completed = True
                        break
                time.sleep(0.3)

            assert reassigned_and_completed, "Task was not recovered and completed by survivor node"

    finally:
        for name, p in reversed(processes):
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
