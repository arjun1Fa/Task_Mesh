"""Automated tests for taskmeshctl CLI commands."""

import argparse
from typing import Generator
import pytest
import httpx
from fastapi.testclient import TestClient

from taskmesh.cli.main import (
    handle_cluster_cmd,
    handle_dlq_cmd,
    handle_node_cmd,
    handle_scheduler_cmd,
    handle_task_cmd,
)
from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import NodeStatus, TaskStatus
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task, TaskCreate
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.orchestrator.server import create_app
from taskmesh.persistence.repositories import MemoryTaskRepository


import sys
import taskmesh.cli.main
cli_module = sys.modules["taskmesh.cli.main"]

@pytest.fixture
def cli_environment(monkeypatch) -> Generator[OrchestratorRuntime, None, None]:
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig()
    runtime = OrchestratorRuntime(repository=repo, config=cfg)
    app = create_app(runtime=runtime)
    client = TestClient(app)

    # Monkeypatch get_client in cli_module to route requests to FastAPI TestClient
    def mock_get_client(base_url: str):
        return client

    monkeypatch.setattr(cli_module, "get_client", mock_get_client)
    yield runtime


def test_cli_task_lifecycle(cli_environment: OrchestratorRuntime, capsys):
    runtime = cli_environment

    # 1. task submit
    args_submit = argparse.Namespace(
        task_action="submit",
        type="log",
        payload='{"message": "cli-test"}',
        priority=5,
        gpu=False,
    )
    handle_task_cmd(args_submit, "http://testserver")
    captured = capsys.readouterr()
    assert "Task submitted successfully:" in captured.out

    # Retrieve created task id
    import json
    data = json.loads(captured.out.split("Task submitted successfully:")[1].strip())
    task_id = data["id"]

    # 2. task get
    args_get = argparse.Namespace(task_action="get", task_id=task_id)
    handle_task_cmd(args_get, "http://testserver")
    captured = capsys.readouterr()
    assert task_id in captured.out

    # 3. task list
    args_list = argparse.Namespace(task_action="list")
    handle_task_cmd(args_list, "http://testserver")
    captured = capsys.readouterr()
    assert task_id in captured.out

    # 4. task cancel
    args_cancel = argparse.Namespace(task_action="cancel", task_id=task_id)
    handle_task_cmd(args_cancel, "http://testserver")
    captured = capsys.readouterr()
    assert "Task cancelled:" in captured.out

    # 5. task retry
    args_retry = argparse.Namespace(task_action="retry", task_id=task_id)
    handle_task_cmd(args_retry, "http://testserver")
    captured = capsys.readouterr()
    assert "Task re-queued for execution:" in captured.out


@pytest.mark.asyncio
async def test_cli_nodes_and_cluster(cli_environment: OrchestratorRuntime, capsys):
    runtime = cli_environment

    # Register mock node
    node = NodeProfile(
        id="cli-node-1",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(cpu_cores=8, supported_handlers=["log"]),
    )
    await runtime.registry.register(node, None)

    # 1. node list
    args_node_list = argparse.Namespace(node_action="list")
    handle_node_cmd(args_node_list, "http://testserver")
    captured = capsys.readouterr()
    assert "cli-node-1" in captured.out

    # 2. node inspect
    args_node_insp = argparse.Namespace(node_action="inspect", node_id="cli-node-1")
    handle_node_cmd(args_node_insp, "http://testserver")
    captured = capsys.readouterr()
    assert "cli-node-1" in captured.out

    # 3. node drain
    args_node_drain = argparse.Namespace(node_action="drain", node_id="cli-node-1")
    handle_node_cmd(args_node_drain, "http://testserver")
    captured = capsys.readouterr()
    assert "draining" in captured.out

    # 4. cluster health
    args_cluster = argparse.Namespace(cluster_action="health")
    handle_cluster_cmd(args_cluster, "http://testserver")
    captured = capsys.readouterr()
    assert "healthy" in captured.out or "total_nodes" in captured.out


@pytest.mark.asyncio
async def test_cli_scheduler_and_dlq(cli_environment: OrchestratorRuntime, capsys):
    runtime = cli_environment

    # 1. scheduler status
    args_sched_status = argparse.Namespace(sched_action="status")
    handle_scheduler_cmd(args_sched_status, "http://testserver")
    captured = capsys.readouterr()
    assert "mode" in captured.out

    # 2. scheduler decisions
    args_sched_dec = argparse.Namespace(sched_action="decisions")
    handle_scheduler_cmd(args_sched_dec, "http://testserver")
    captured = capsys.readouterr()
    assert "[]" in captured.out

    # Add item to DLQ
    failed_task = Task(id="dlq-task-1", task_type="log", status=TaskStatus.FAILED)
    await runtime.repo.save(failed_task)
    await runtime.dlq.add(failed_task, final_error="Max retries reached")

    # 3. dlq list
    args_dlq_list = argparse.Namespace(dlq_action="list")
    handle_dlq_cmd(args_dlq_list, "http://testserver")
    captured = capsys.readouterr()
    assert "dlq-task-1" in captured.out

    # 4. dlq recover
    args_dlq_recover = argparse.Namespace(dlq_action="recover", task_id="dlq-task-1")
    handle_dlq_cmd(args_dlq_recover, "http://testserver")
    captured = capsys.readouterr()
    assert "Task recovered from DLQ:" in captured.out
