"""Tabular Q-learning policy with bounded state and candidate-slot action space."""

import random
from typing import Dict, List, Optional, Tuple
from taskmesh.core.models import NodeProfile, Task


class QLearningScheduler:
    """Tabular Q-learning model for selecting among ranked candidate nodes.
    
    Actions are bounded candidate slots:
    - 0: Top-ranked candidate
    - 1: 2nd-ranked candidate
    - 2: 3rd-ranked candidate
    """

    NUM_ACTIONS = 3  # Slot 0, 1, 2

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon: float = 0.15,
    ) -> None:
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        # Q-table: state_tuple -> list of Q-values [q_slot0, q_slot1, q_slot2]
        self.q_table: Dict[Tuple[int, int, int], List[float]] = {}

    def discretize_state(self, top_candidate: NodeProfile, task: Task) -> Tuple[int, int, int]:
        """Maps continuous metrics to discrete state bucket tuple:
        (score_bucket, load_bucket, priority_bucket)
        """
        # Score bucket (0: < 0.8, 1: 0.8 - 1.5, 2: > 1.5)
        eff_score = top_candidate.effective_score
        if eff_score < 0.8:
            score_b = 0
        elif eff_score <= 1.5:
            score_b = 1
        else:
            score_b = 2

        # Load bucket (0: < 40%, 1: 40-75%, 2: > 75%)
        avg_load = 50.0
        if top_candidate.telemetry:
            avg_load = (top_candidate.telemetry.cpu_percent + top_candidate.telemetry.ram_percent) / 2.0
        if avg_load < 40.0:
            load_b = 0
        elif avg_load <= 75.0:
            load_b = 1
        else:
            load_b = 2

        # Priority bucket (0: <= 0, 1: 1 - 10, 2: > 10)
        if task.priority <= 0:
            prio_b = 0
        elif task.priority <= 10:
            prio_b = 1
        else:
            prio_b = 2

        return (score_b, load_b, prio_b)

    def select_action(
        self,
        state: Tuple[int, int, int],
        num_candidates: int,
    ) -> int:
        """Selects candidate slot using epsilon-greedy exploration."""
        max_valid_action = min(self.NUM_ACTIONS, num_candidates) - 1
        if max_valid_action <= 0:
            return 0

        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            return random.randint(0, max_valid_action)

        # Exploitation
        q_values = self.q_table.get(state, [0.0] * self.NUM_ACTIONS)
        valid_q = q_values[: max_valid_action + 1]
        best_val = max(valid_q)
        # Random tie-breaker among best
        best_actions = [i for i, v in enumerate(valid_q) if v == best_val]
        return random.choice(best_actions)

    def update(
        self,
        state: Tuple[int, int, int],
        action: int,
        reward: float,
        next_state: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """Q-learning Bellman update: Q(s, a) <- Q(s, a) + lr * (r + gamma * max_a' Q(s', a') - Q(s, a))."""
        if state not in self.q_table:
            self.q_table[state] = [0.0] * self.NUM_ACTIONS

        current_q = self.q_table[state][action]

        if next_state is not None and next_state in self.q_table:
            max_next_q = max(self.q_table[next_state])
        else:
            max_next_q = 0.0

        target = reward + (self.gamma * max_next_q)
        self.q_table[state][action] = current_q + self.lr * (target - current_q)

    @staticmethod
    def calculate_reward(success: bool, execution_time: float, timeout_seconds: float) -> float:
        """Calculates scalar reward for task outcome."""
        if not success:
            return -1.5

        reward = 1.0
        # Bonus for fast execution well within timeout
        if timeout_seconds > 0 and execution_time < (timeout_seconds * 0.5):
            reward += 0.5
        return reward
