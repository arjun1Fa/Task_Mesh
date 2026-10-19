"""Tests for Tabular Q-Learning bounded action space, dynamic nodes, and MWU outcomes."""

import pytest
from taskmesh.core.models import NodeCapabilities, NodeProfile, Task
from taskmesh.learning.mwu import MWUWeightLearner
from taskmesh.learning.qlearning import QLearningScheduler


def test_qlearning_unseen_and_known_state():
    rl = QLearningScheduler(learning_rate=0.2, discount_factor=0.9, epsilon=0.0)

    # 1. Unseen state
    unseen_state = (2, 2, 2)
    assert unseen_state not in rl.q_table
    action = rl.select_action(unseen_state, num_candidates=3)
    assert action in (0, 1, 2)

    # 2. Train state to prefer slot 1
    rl.update(unseen_state, action=1, reward=10.0)
    assert unseen_state in rl.q_table
    assert rl.q_table[unseen_state][1] > rl.q_table[unseen_state][0]

    # In exploitation mode (epsilon=0.0), action must be slot 1
    best_action = rl.select_action(unseen_state, num_candidates=3)
    assert best_action == 1


def test_qlearning_bounded_action_on_node_join_and_leave():
    rl = QLearningScheduler(learning_rate=0.2, discount_factor=0.9, epsilon=0.0)
    state = (1, 1, 1)
    rl.update(state, action=2, reward=5.0)  # Slot 2 has highest Q-value

    # Case A: 3 candidates available -> Can pick slot 2
    action_3 = rl.select_action(state, num_candidates=3)
    assert action_3 == 2

    # Case B: Node leaves -> Only 2 candidates available -> Action MUST be bounded to <= 1
    action_2 = rl.select_action(state, num_candidates=2)
    assert action_2 in (0, 1)

    # Case C: Only 1 candidate -> Action MUST be 0
    action_1 = rl.select_action(state, num_candidates=1)
    assert action_1 == 0

    # Case D: Node joins -> 5 candidates available -> Action remains bounded to NUM_ACTIONS (0..2)
    action_5 = rl.select_action(state, num_candidates=5)
    assert action_5 in (0, 1, 2)


def test_mwu_weight_evolution_across_diverse_outcomes():
    mwu = MWUWeightLearner(eta=0.2)
    initial_weights = mwu.get_weights().copy()

    # Scenario 1: CPU-heavy workload with high CPU delay (high cpu loss)
    for _ in range(5):
        mwu.update({
            "cpu": 0.9,
            "gpu": 0.1,
            "load": 0.2,
            "latency": 0.1,
            "reliability": 0.0,
        })
    weights_after_cpu_stress = mwu.get_weights()
    # High CPU loss should penalize CPU factor weight relative to GPU and reliability
    assert weights_after_cpu_stress["cpu"] < initial_weights["cpu"]
    assert weights_after_cpu_stress["reliability"] > weights_after_cpu_stress["cpu"]

    # Scenario 2: Node unreliability (high reliability loss)
    for _ in range(10):
        mwu.update({
            "cpu": 0.1,
            "gpu": 0.1,
            "load": 0.1,
            "latency": 0.1,
            "reliability": 1.0,
        })
    weights_after_failures = mwu.get_weights()
    assert weights_after_failures["reliability"] < weights_after_cpu_stress["reliability"]
    assert abs(sum(weights_after_failures.values()) - 1.0) < 1e-3


def test_qlearning_epsilon_decay():
    rl = QLearningScheduler(learning_rate=0.1, discount_factor=0.9, epsilon=0.15, epsilon_min=0.01, epsilon_decay=0.9)
    assert rl.epsilon == 0.15
    state = (1, 1, 1)
    rl.update(state, action=0, reward=1.0)
    assert rl.epsilon < 0.15
    for _ in range(50):
        rl.update(state, action=0, reward=1.0)
    assert rl.epsilon == 0.01

