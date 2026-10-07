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
