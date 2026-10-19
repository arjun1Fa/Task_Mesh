"""Unit tests for EWMA scoring, DRR fairness, MWU weights, and Q-learning."""

import pytest
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task
from taskmesh.fairness.drr import DRRFairnessManager, calculate_fairness_cv
from taskmesh.learning.mwu import MWUWeightLearner
from taskmesh.learning.qlearning import QLearningScheduler
from taskmesh.scoring.base_score import EWMAUpdater, compute_base_score


def test_base_score_and_ewma():
    profile = NodeProfile(
        id="node-gpu",
        capabilities=NodeCapabilities(
            cpu_cores=8,
            cpu_frequency_mhz=3200.0,
            ram_total_mb=16384,
            has_gpu=True,
        )
    )
    score = compute_base_score(profile)
    assert score > 1.5

    ewma = EWMAUpdater(alpha=0.2)
    # If completed twice as fast (expected 10s, actual 5s -> ratio = 2.0)
    mult = ewma.update_multiplier(current_multiplier=1.0, expected_duration_seconds=10.0, actual_duration_seconds=5.0)
    assert mult > 1.0


def test_drr_fairness_and_cv():
    drr = DRRFairnessManager(base_quantum=2.0)
    n1 = NodeProfile(id="n1", base_score=1.0)
    n2 = NodeProfile(id="n2", base_score=2.0)

    drr.update_quantum_and_deficits([n1, n2])
    assert drr.get_deficit("n2") > drr.get_deficit("n1")

    chosen = drr.select_fair_node([n1, n2], cost=1.0)
    assert chosen.id == "n2"

    # Fairness CV test
    cv_balanced = calculate_fairness_cv([10, 10, 10])
    assert cv_balanced == 0.0

    cv_unbalanced = calculate_fairness_cv([20, 5, 2])
    assert cv_unbalanced > 0.5


def test_mwu_weight_adaptation():
    mwu = MWUWeightLearner(eta=0.5)
    init_weights = mwu.get_weights()
    assert abs(sum(init_weights.values()) - 1.0) < 1e-3

    # High loss on GPU, low loss on CPU
    updated = mwu.update({"cpu": 0.0, "gpu": 1.0, "load": 0.5, "latency": 0.5, "reliability": 0.5})
    # CPU weight should be higher than GPU weight
    assert updated["cpu"] > updated["gpu"]
    assert abs(sum(updated.values()) - 1.0) < 1e-3


def test_qlearning_state_and_update():
    rl = QLearningScheduler(learning_rate=0.2, discount_factor=0.9, epsilon=0.0)
    node = NodeProfile(id="n1", base_score=1.2)
    task = Task(task_type="cpu", priority=5)

    state = rl.discretize_state(node, task)
    assert isinstance(state, tuple)
    assert len(state) == 3

    action = rl.select_action(state, num_candidates=3)
    assert action in (0, 1, 2)

    # Bellman update
    rl.update(state, action=0, reward=2.0)
    assert rl.q_table[state][0] > 0.0


@pytest.mark.asyncio
async def test_adaptive_scheduler_ablations():
    from taskmesh.scheduler.adaptive import AdaptiveScheduler

    nodes = [
        NodeProfile(id="n1", base_score=2.0, capabilities=NodeCapabilities(cpu_cores=8, ram_total_mb=16384)),
        NodeProfile(id="n2", base_score=1.0, capabilities=NodeCapabilities(cpu_cores=4, ram_total_mb=8192)),
    ]
    task = Task(id="t1", task_type="cpu_test", priority=10)

    # 1. Full Adaptive
    sched_full = AdaptiveScheduler()
    dec_full = await sched_full.select_node(task, nodes)
    assert dec_full.selected_node_id in ("n1", "n2")

    # 2. Without DRR
    sched_no_drr = AdaptiveScheduler(enable_drr=False)
    dec_no_drr = await sched_no_drr.select_node(task, nodes)
    assert dec_no_drr.selected_node_id in ("n1", "n2")

    # 3. Without Bidding
    sched_no_bid = AdaptiveScheduler(enable_bidding=False)
    dec_no_bid = await sched_no_bid.select_node(task, nodes)
    assert dec_no_bid.selected_node_id in ("n1", "n2")

    # 4. Without MWU
    sched_no_mwu = AdaptiveScheduler(enable_mwu=False)
    dec_no_mwu = await sched_no_mwu.select_node(task, nodes)
    assert dec_no_mwu.selected_node_id in ("n1", "n2")

    # 5. Without RL
    sched_no_rl = AdaptiveScheduler(enable_rl=False)
    dec_no_rl = await sched_no_rl.select_node(task, nodes)
    assert dec_no_rl.selected_node_id in ("n1", "n2")
    assert dec_no_rl.rl_state is None
    assert dec_no_rl.rl_action == 0

    # 6. Without Wireless Cost
    sched_no_wc = AdaptiveScheduler(enable_wireless_cost=False)
    dec_no_wc = await sched_no_wc.select_node(task, nodes)
    assert dec_no_wc.selected_node_id in ("n1", "n2")
    assert "direct selection without wireless cost" in dec_no_wc.offload_reason

    # 7. EWMA update (faster than expected yields > 1.0; slower yields < 1.0)
    node_copy = nodes[0].model_copy()
    await sched_full.record_task_outcome(node_copy, task, dec_full, actual_duration_seconds=0.0001, success=True)
    assert node_copy.performance_multiplier > 1.0

    node_slow = nodes[0].model_copy()
    await sched_full.record_task_outcome(node_slow, task, dec_full, actual_duration_seconds=20.0, success=True)
    assert node_slow.performance_multiplier < 1.0

    # Without EWMA update
    node_no_ewma = nodes[0].model_copy()
    sched_no_ewma = AdaptiveScheduler(enable_ewma=False)
    await sched_no_ewma.record_task_outcome(node_no_ewma, task, dec_full, actual_duration_seconds=0.0001, success=True)
    assert node_no_ewma.performance_multiplier == 1.0

