"""Real end-to-end multi-process distributed test over actual WebSockets."""

import os
import subprocess
import sys
import tempfile
import time
import httpx
import pytest


@pytest.mark.asyncio
async def test_independent_os_process_cluster_execution():
    """Validates real multi-process distributed execution:
    - 1 Orchestrator OS process
    - 3 Node Agent OS processes
    - Actual WebSocket connections
    - Real task dispatch and execution
    """
    python_bin = sys.executable
    port = 8210
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    processes = []

    try:
        # 1. Start Orchestrator OS process
        orch_cmd = [
            python_bin, "-m", "taskmesh.orchestrator.main",
            "--port", str(port),
            "--db", db_path,
        ]
        p_orch = subprocess.Popen(orch_cmd)
        processes.append(("Orchestrator", p_orch))

        # Wait for orchestrator to be ready
        ready = False
        async with httpx.AsyncClient(timeout=2.0) as client:
            for _ in range(25):
                try:
                    resp = await client.get(f"http://127.0.0.1:{port}/v1/cluster/health")
                    if resp.status_code == 200:
                        ready = True
                        break
                except Exception:
                    time.sleep(0.2)
        assert ready, "Orchestrator failed to start within timeout"

        # 2. Start 3 independent Node Agent processes
        ws_url = f"ws://127.0.0.1:{port}/v1/ws/nodes"
        node_names = ["node-a", "node-b", "node-c"]
        for name in node_names:
            cmd = [
                python_bin, "-m", "taskmesh.node.main",
                "--node-id", name,
                "--url", ws_url,
                "--workers", "2",
            ]
            p_node = subprocess.Popen(cmd)
            processes.append((name, p_node))

        # 3. Wait for all 3 nodes to connect and register
        nodes_registered = False
        async with httpx.AsyncClient(timeout=2.0) as client:
            for _ in range(30):
                resp = await client.get(f"http://127.0.0.1:{port}/v1/cluster/health")
                if resp.status_code == 200:
                    health = resp.json()
                    if health.get("online_nodes", 0) >= 3:
                        nodes_registered = True
                        break
                time.sleep(0.2)
        assert nodes_registered, "Nodes failed to register within timeout"

        # 4. Submit 6 tasks to the cluster
        task_ids = []
        async with httpx.AsyncClient(timeout=5.0) as client:
            for i in range(6):
                req = {
                    "task_type": "log" if i % 2 == 0 else "cpu_test",
                    "payload": {"message": f"distributed-task-{i}", "iterations": 500},
                    "priority": i + 1,
                }
                resp = await client.post(f"http://127.0.0.1:{port}/v1/tasks", json=req)
                assert resp.status_code == 201
                task_ids.append(resp.json()["id"])

            # 5. Wait for all 6 tasks to complete
            all_completed = False
            for _ in range(40):
                completed_count = 0
                for tid in task_ids:
                    t_resp = await client.get(f"http://127.0.0.1:{port}/v1/tasks/{tid}")
                    if t_resp.status_code == 200 and t_resp.json().get("status") == "completed":
                        completed_count += 1
                if completed_count == len(task_ids):
                    all_completed = True
                    break
                time.sleep(0.25)

            assert all_completed, f"Only {completed_count}/{len(task_ids)} tasks completed"

            # 6. Verify work was distributed across independent node processes
            assigned_nodes = set()
            for tid in task_ids:
                t_resp = await client.get(f"http://127.0.0.1:{port}/v1/tasks/{tid}")
                task_data = t_resp.json()
                assert task_data["status"] == "completed"
                assert task_data["result"] is not None
                assigned_nodes.add(task_data["assigned_node_id"])

            assert len(assigned_nodes) >= 2, f"Expected multiple nodes used, got: {assigned_nodes}"

    finally:
        # Cleanly terminate all child processes
        for name, p in reversed(processes):
            try:
                p.terminate()
                p.wait(timeout=1.5)
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
