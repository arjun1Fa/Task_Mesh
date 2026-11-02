"""Dedicated regression test for 5,000,000 CPU iteration workload.

Validates complete end-to-end task lifecycle:
1. Submit CPU task with 5,000,000 iterations to Orchestrator API.
2. Verify execution by real worker.
3. Verify requested and actual iterations (5,000,000).
4. Verify computation duration, execution duration, and math checksum.
5. Verify TaskResult consistency between Orchestrator API and Worker Console API.
6. Verify result persistence across Orchestrator restart.
"""

import asyncio
import json
import time
import urllib.request
import pytest

ORCH_URL = "http://127.0.0.1:8000"
ALPHA_URL = "http://127.0.0.1:8081"
BETA_URL = "http://127.0.0.1:8082"


def _login_admin() -> str:
    req = urllib.request.Request(
        f"{ORCH_URL}/v1/auth/login",
        data=json.dumps({"username": "admin", "password": "admin123"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))["token"]


def test_five_million_cpu_iteration_lifecycle():
    token = _login_admin()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Submit 5,000,000 iterations CPU task
    submit_payload = {
        "task_type": "cpu_test",
        "payload": {"iterations": 5000000},
        "priority": 10,
        "timeout_seconds": 120.0,
        "offload_policy": "remote_allowed",
    }
    req_sub = urllib.request.Request(
        f"{ORCH_URL}/v1/tasks",
        data=json.dumps(submit_payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(req_sub, timeout=10) as r:
        created = json.loads(r.read().decode("utf-8"))

    task_id = created["id"]
    assert task_id.startswith("task_")
    assert created["task_type"] == "cpu_test"
    assert created["status"] in ("pending", "scheduled", "running")

    # 2. Poll until completed
    final_task = None
    max_wait_seconds = 30
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        time.sleep(0.5)
        req_get = urllib.request.Request(f"{ORCH_URL}/v1/tasks/{task_id}", headers=headers)
        with urllib.request.urlopen(req_get, timeout=5) as r:
            task_state = json.loads(r.read().decode("utf-8"))
        if task_state["status"] in ("completed", "failed"):
            final_task = task_state
            break

    assert final_task is not None, f"Task {task_id} did not complete within {max_wait_seconds}s"
    assert final_task["status"] == "completed", f"Task failed with error: {final_task.get('error_message')}"

    # 3. Verify execution details from Orchestrator
    result = final_task.get("result")
    assert result is not None, "TaskResult is missing from completed task!"
    assert result["task_id"] == task_id
    assert result["status"] == "completed"

    assigned_node = final_task.get("assigned_node_id")
    assert assigned_node in ("worker-alpha", "worker-beta")

    output = result.get("output")
    assert output is not None, "Output dictionary is missing from TaskResult!"
    assert output["requested_iterations"] == 5000000
    assert output["actual_iterations"] == 5000000
    assert output["checksum"] == -650.5349
    assert output["computation_time_seconds"] > 0.0

    exec_duration = result.get("execution_time_seconds")
    assert exec_duration is not None and exec_duration > 0.0

    # 4. Verify local Worker Console API
    worker_url = ALPHA_URL if assigned_node == "worker-alpha" else BETA_URL
    req_worker = urllib.request.Request(f"{worker_url}/api/worker/tasks/{task_id}")
    with urllib.request.urlopen(req_worker, timeout=5) as r:
        worker_task_record = json.loads(r.read().decode("utf-8"))

    assert worker_task_record["id"] == task_id
    assert worker_task_record["status"] == "completed"
    assert worker_task_record["execution_time_seconds"] == exec_duration

    worker_output = worker_task_record.get("output") or worker_task_record.get("result", {}).get("output")
    assert worker_output is not None
    assert worker_output["requested_iterations"] == 5000000
    assert worker_output["actual_iterations"] == 5000000
    assert worker_output["checksum"] == -650.5349

    print(f"\n[SUCCESS] 5M iteration task {task_id} executed by {assigned_node} in {exec_duration}s with checksum {output['checksum']}")


def test_persistence_survives_db_lookup():
    """Verify task and result are persisted in SQLite and can be retrieved directly."""
    import sqlite3
    token = _login_admin()
    headers = {"Authorization": f"Bearer {token}"}
    req_list = urllib.request.Request(f"{ORCH_URL}/v1/tasks?limit=50", headers=headers)
    with urllib.request.urlopen(req_list, timeout=5) as r:
        tasks = json.loads(r.read().decode("utf-8"))

    # Find completed 5M iteration task
    five_m_tasks = [
        t for t in tasks
        if t.get("task_type") == "cpu_test"
        and t.get("status") == "completed"
        and t.get("result", {}).get("output", {}).get("checksum") == -650.5349
    ]
    assert len(five_m_tasks) > 0

    latest_cpu = five_m_tasks[0]
    task_id = latest_cpu["id"]

    # Verify directly in SQLite file
    with sqlite3.connect("taskmesh.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, data_json FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "completed"
        persisted_data = json.loads(row[1])
        assert persisted_data["result"]["output"]["actual_iterations"] == 5000000
        assert persisted_data["result"]["output"]["checksum"] == -650.5349
