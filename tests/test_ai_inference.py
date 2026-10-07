"""Tests for AI inference task handling and GPU eligibility enforcement."""

import pytest
from taskmesh.core.enums import NodeStatus, TaskStatus
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task, TaskCreate
from taskmesh.handlers.ai_inference import image_inference_handler
from taskmesh.node.worker_pool import WorkerPool
from taskmesh.protocol.messages import TaskAssignmentPayload
from taskmesh.scheduler.base import filter_eligible_nodes


def test_image_inference_handler_execution():
    """Verify image_inference handler executes on synthetic tensor inputs."""
    payload = {
        "model": "yolov8n",
        "batch_size": 2,
        "image_dim": 128,
        "use_gpu": False,
    }
    result = image_inference_handler(payload)
    assert result["model"] == "yolov8n"
    assert "backend" in result
    assert result["input_dim"] == [2, 3, 128, 128]
    assert "inference_latency_ms" in result
    assert result["inference_latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_worker_pool_ai_inference():
    """Verify worker pool can register and execute AI inference tasks."""
    pool = WorkerPool(concurrency=2)
    pool.register_handler("image_inference", image_inference_handler)

    from taskmesh.core.models import utc_now
    assignment = TaskAssignmentPayload(
        task_id="ai-test-1",
        attempt_id="ai-test-1-A1",
        lease_id="lease-ai-1",
        lease_expires_at=utc_now(),
        task_type="image_inference",
        payload={"batch_size": 1, "image_dim": 64},
        priority=10,
        timeout_seconds=5.0,
    )

    res = await pool.execute_assignment(assignment, node_id="test-gpu-node")
    assert res.status == TaskStatus.COMPLETED
    assert res.output["model"] == "yolov8n"
    await pool.shutdown()


def test_gpu_requirement_gating():
    """Verify GPU-requiring tasks are never assigned to CPU-only nodes."""
    cpu_node = NodeProfile(
        id="cpu-node-1",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            has_gpu=False,
            supported_handlers=["image_inference", "log"],
            tags=["cpu-only"],
        ),
    )
    gpu_node = NodeProfile(
        id="gpu-node-1",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            has_gpu=True,
            supported_handlers=["image_inference", "log"],
            tags=["cuda", "rtx4090"],
        ),
    )

    candidates = [cpu_node, gpu_node]

    # Task requiring GPU
    task_needs_gpu = Task(task_type="image_inference", requires_gpu=True)
    eligible = filter_eligible_nodes(task_needs_gpu, candidates)
    assert len(eligible) == 1
    assert eligible[0].id == "gpu-node-1"

    # Task without GPU requirement can use both
    task_generic = Task(task_type="image_inference", requires_gpu=False)
    eligible_generic = filter_eligible_nodes(task_generic, candidates)
    assert len(eligible_generic) == 2
