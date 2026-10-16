"""Unit tests for Candidate Eligibility Filtering and Checkpointing."""

import pytest
from taskmesh.checkpoint.manager import CheckpointManager
from taskmesh.core.enums import NodeStatus
from taskmesh.core.models import CheckpointData, NodeCapabilities, NodeProfile, Task
from taskmesh.scheduler.base import filter_eligible_nodes


def test_candidate_eligibility_filtering():
    n_gpu = NodeProfile(
        id="n_gpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            has_gpu=True,
            ram_available_mb=8192,
            supported_handlers=["image_inference", "log"],
            tags=["cuda", "high-mem"],
        )
    )
    n_cpu = NodeProfile(
        id="n_cpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(
            has_gpu=False,
            ram_available_mb=2048,
            supported_handlers=["cpu_test", "log"],
            tags=["general"],
        )
    )
    n_offline = NodeProfile(
        id="n_offline",
        status=NodeStatus.OFFLINE,
        capabilities=NodeCapabilities(has_gpu=True, supported_handlers=["log"])
    )

    candidates = [n_gpu, n_cpu, n_offline]

    # Task requiring GPU
    task_gpu = Task(task_type="image_inference", requires_gpu=True)
    eligible_gpu = filter_eligible_nodes(task_gpu, candidates)
    assert len(eligible_gpu) == 1
    assert eligible_gpu[0].id == "n_gpu"

    # Task requiring memory > 4096MB
    task_mem = Task(task_type="log", required_memory_mb=4096)
    eligible_mem = filter_eligible_nodes(task_mem, candidates)
    assert len(eligible_mem) == 1
    assert eligible_mem[0].id == "n_gpu"

    # Offline nodes never eligible
    task_log = Task(task_type="log")
    eligible_log = filter_eligible_nodes(task_log, candidates)
    assert all(n.status == NodeStatus.ONLINE for n in eligible_log)


@pytest.mark.asyncio
async def test_checkpoint_manager():
    mgr = CheckpointManager()
    cp = CheckpointData(
        task_id="t_batch",
        attempt_id="t_batch-A1",
        step=50,
        state={"processed_records": 5000},
    )
    await mgr.save_checkpoint(cp)

    retrieved = await mgr.get_latest_checkpoint("t_batch")
    assert retrieved is not None
    assert retrieved.step == 50
    assert retrieved.state["processed_records"] == 5000

    task = Task(id="t_batch", task_type="batch")
    await mgr.attach_checkpoint(task)
    assert task.latest_checkpoint is not None
    assert task.latest_checkpoint.step == 50


@pytest.mark.asyncio
async def test_baseline_tie_breaking():
    from taskmesh.scheduler.baseline import LeastLoadedScheduler, HighestBidScheduler
    
    n1 = NodeProfile(id="n1", status=NodeStatus.ONLINE, base_score=1.0)
    n2 = NodeProfile(id="n2", status=NodeStatus.ONLINE, base_score=1.0)
    candidates = [n1, n2]
    task = Task(id="t1", task_type="cpu_test")
    
    ll = LeastLoadedScheduler()
    dec1 = await ll.select_node(task, candidates)
    dec2 = await ll.select_node(task, candidates)
    # With tie-breaking, consecutive selections rotate among tied candidates
    assert {dec1.selected_node_id, dec2.selected_node_id} == {"n1", "n2"}

    hb = HighestBidScheduler()
    dec_hb1 = await hb.select_node(task, candidates)
    dec_hb2 = await hb.select_node(task, candidates)
    assert {dec_hb1.selected_node_id, dec_hb2.selected_node_id} == {"n1", "n2"}

