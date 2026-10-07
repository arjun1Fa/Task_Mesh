"""End-to-end demonstration and test of EWMA dynamic performance adaptation."""

import pytest
from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.core.enums import NodeStatus, SchedulerMode
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.decision import SchedulerDecision


@pytest.mark.asyncio
async def test_ewma_performance_multiplier_adaptation():
    """Demonstrates that fast task completion boosts a node's performance multiplier
    and effective score, while slow execution degrades it, causing Contract-Net
    to adapt its ranking."""
    # 1. Setup two identical nodes initially
    node_a = NodeProfile(
        id="node-fast",
        status=NodeStatus.ONLINE,
        base_score=1.0,
        performance_multiplier=1.0,
        capabilities=NodeCapabilities(cpu_cores=4, supported_handlers=["cpu_test"]),
    )
    node_b = NodeProfile(
        id="node-slow",
        status=NodeStatus.ONLINE,
        base_score=1.0,
        performance_multiplier=1.0,
        capabilities=NodeCapabilities(cpu_cores=4, supported_handlers=["cpu_test"]),
    )

    assert node_a.effective_score == 1.0
    assert node_b.effective_score == 1.0

    scheduler = AdaptiveScheduler(ewma_alpha=0.3)
    task = Task(task_type="cpu_test", timeout_seconds=2.0)

    # 2. Simulate Node A executing repeatedly fast (0.05s)
    # Expected duration for timeout 2.0 is 0.4s
    for _ in range(5):
        decision = SchedulerDecision(
            task_id=task.id,
            selected_node_id=node_a.id,
            policy_used=SchedulerMode.ADAPTIVE,
        )
        await scheduler.record_task_outcome(
            node=node_a,
            task=task,
            decision=decision,
            actual_duration_seconds=0.05,
            success=True,
        )

    # 3. Simulate Node B executing repeatedly slow (1.8s)
    for _ in range(5):
        decision = SchedulerDecision(
            task_id=task.id,
            selected_node_id=node_b.id,
            policy_used=SchedulerMode.ADAPTIVE,
        )
        await scheduler.record_task_outcome(
            node=node_b,
            task=task,
            decision=decision,
            actual_duration_seconds=1.8,
            success=True,
        )

    # 4. Verify divergence in performance multiplier and effective score
    assert node_a.performance_multiplier > 1.5, f"Node A multiplier should increase: {node_a.performance_multiplier}"
    assert node_b.performance_multiplier < 0.8, f"Node B multiplier should decrease: {node_b.performance_multiplier}"
    assert node_a.effective_score > node_b.effective_score * 2.0

    # 5. Evaluate Contract-Net bids: Node A must submit a substantially higher bid
    candidates = [node_b, node_a]
    bid_a = calculate_node_bid(node_a, task, scheduler.mwu.get_weights())
    bid_b = calculate_node_bid(node_b, task, scheduler.mwu.get_weights())

    assert bid_a > bid_b, f"Node A bid ({bid_a}) must exceed Node B bid ({bid_b})"
    
    # 6. Verify AdaptiveScheduler selects Node A over Node B
    selected_decision = await scheduler.select_node(task, candidates)
    assert selected_decision.selected_node_id == node_a.id
