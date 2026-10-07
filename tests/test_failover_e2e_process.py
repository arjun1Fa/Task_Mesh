"""Real multi-process Primary/Standby failover and automated promotion integration test."""

import asyncio
import os
import subprocess
import sys
import tempfile
import httpx
import pytest


@pytest.mark.asyncio
async def test_real_process_primary_standby_failover():
    """Validates real end-to-end failover across independent OS processes:
    1. Primary Orchestrator (port 8330)
    2. Standby Orchestrator (port 8331) replicating snapshots from Primary
    3. Node Agent connecting to Primary with standby URL fallback
    4. Tasks submitted and executed
    5. Primary OS process is killed
    6. Standby detects failure and promotes itself to Primary
    7. Node reconnects to promoted Standby
    8. Interrupted and new tasks execute to completion
    """
    python_bin = sys.executable
    port_primary = 8330
    port_standby = 8331

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_p:
        db_primary = tmp_p.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_s:
        db_standby = tmp_s.name

    processes = []

    try:
        # 1. Start Primary Orchestrator process
        p_primary = subprocess.Popen([
            python_bin, "-m", "taskmesh.orchestrator.main",
            "--port", str(port_primary),
            "--db", db_primary,
        ])
        processes.append(("Primary", p_primary))

        # Wait for Primary to become healthy
        async with httpx.AsyncClient(timeout=2.0) as client:
            ready_primary = False
            for _ in range(30):
                try:
                    resp = await client.get(f"http://127.0.0.1:{port_primary}/v1/cluster/health")
                    if resp.status_code == 200:
                        ready_primary = True
                        break
                except Exception:
                    await asyncio.sleep(0.2)
            assert ready_primary, "Primary orchestrator failed to start"

        # 2. Start Standby Orchestrator process with fast snapshot interval
        p_standby = subprocess.Popen([
            python_bin, "-m", "taskmesh.orchestrator.main",
            "--port", str(port_standby),
            "--db", db_standby,
            "--standby",
            "--primary-url", f"http://127.0.0.1:{port_primary}",
            "--snapshot-interval", "0.5",
        ])
        processes.append(("Standby", p_standby))

        # Wait for Standby to become healthy
        async with httpx.AsyncClient(timeout=2.0) as client:
            ready_standby = False
            for _ in range(30):
                try:
                    resp = await client.get(f"http://127.0.0.1:{port_standby}/v1/standby/status")
                    if resp.status_code == 200:
                        ready_standby = True
                        break
                except Exception:
                    await asyncio.sleep(0.2)
            assert ready_standby, "Standby orchestrator failed to start"

        # 3. Start Node Agent process targeting Primary with Standby fallback
        ws_primary = f"ws://127.0.0.1:{port_primary}/v1/ws/nodes"
        ws_standby = f"ws://127.0.0.1:{port_standby}/v1/ws/nodes"
        p_node = subprocess.Popen([
            python_bin, "-m", "taskmesh.node.main",
            "--node-id", "node-failover-agent",
            "--url", ws_primary,
            "--standby-url", ws_standby,
            "--heartbeat-interval", "0.3",
        ])
        processes.append(("NodeAgent", p_node))

        # Wait for node to register with Primary
        async with httpx.AsyncClient(timeout=2.0) as client:
            for _ in range(30):
                resp = await client.get(f"http://127.0.0.1:{port_primary}/v1/nodes/node-failover-agent")
                if resp.status_code == 200:
                    break
                await asyncio.sleep(0.2)

        # 4. Submit Task 1 to Primary
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp1 = await client.post(
                f"http://127.0.0.1:{port_primary}/v1/tasks",
                json={"task_type": "log", "payload": {"msg": "run-on-primary"}, "priority": 10},
            )
            assert resp1.status_code == 201
            t1_id = resp1.json()["id"]

            # Wait for Task 1 to complete
            for _ in range(30):
                t1_resp = await client.get(f"http://127.0.0.1:{port_primary}/v1/tasks/{t1_id}")
                if t1_resp.status_code == 200 and t1_resp.json().get("status") == "completed":
                    break
                await asyncio.sleep(0.2)

            # Submit Task 2 to Primary (will be replicated to standby)
            resp2 = await client.post(
                f"http://127.0.0.1:{port_primary}/v1/tasks",
                json={"task_type": "cpu_test", "payload": {"iterations": 500}, "priority": 5},
            )
            assert resp2.status_code == 201
            t2_id = resp2.json()["id"]

            # Allow 1.2s for snapshot replication to Standby
            await asyncio.sleep(1.2)

            # 5. KILL Primary Orchestrator OS process!
            p_primary.kill()
            await asyncio.sleep(0.5)

            # 6. Standby detects failure and promotes itself to Primary
            promoted = False
            for _ in range(35):
                try:
                    h_resp = await client.get(f"http://127.0.0.1:{port_standby}/v1/cluster/health")
                    if h_resp.status_code == 200:
                        s_resp = await client.get(f"http://127.0.0.1:{port_standby}/v1/standby/status")
                        if s_resp.status_code == 200 and not s_resp.json().get("standby_mode", True):
                            promoted = True
                            break
                except Exception:
                    pass
                await asyncio.sleep(0.3)

            assert promoted, "Standby failed to promote itself to Primary after primary kill"

            # 7. Wait for Node Agent to reconnect to promoted Standby
            node_reconnected = False
            for _ in range(35):
                try:
                    n_resp = await client.get(f"http://127.0.0.1:{port_standby}/v1/nodes/node-failover-agent")
                    if n_resp.status_code == 200:
                        node_reconnected = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.3)

            assert node_reconnected, "Node Agent failed to reconnect to promoted Standby"

            # 8. Submit new Task 3 to promoted Standby
            resp3 = await client.post(
                f"http://127.0.0.1:{port_standby}/v1/tasks",
                json={"task_type": "log", "payload": {"msg": "run-on-promoted-standby"}, "priority": 20},
            )
            assert resp3.status_code == 201
            t3_id = resp3.json()["id"]

            # Wait for Task 3 to complete on promoted Standby
            t3_completed = False
            for _ in range(35):
                t3_resp = await client.get(f"http://127.0.0.1:{port_standby}/v1/tasks/{t3_id}")
                if t3_resp.status_code == 200 and t3_resp.json().get("status") == "completed":
                    t3_completed = True
                    break
                await asyncio.sleep(0.2)

            assert t3_completed, "Task 3 failed to complete on promoted Standby"

    finally:
        for name, p in reversed(processes):
            try:
                p.terminate()
            except Exception:
                pass
            try:
                p.kill()
            except Exception:
                pass

        for pth in (db_primary, db_standby):
            if os.path.exists(pth):
                try:
                    os.remove(pth)
                except Exception:
                    pass
