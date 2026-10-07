"""Deficit Round Robin (DRR) with adaptive quantum for multi-node fairness."""

from typing import Dict, List, Optional
import numpy as np

from taskmesh.core.models import NodeProfile, Task


class DRRFairnessManager:
    """Fairness controller using Deficit Round Robin with adaptive quantum.
    
    Prevents node starvation while allowing higher-capacity nodes to carry proportional load.
    
    In true DRR:
    - Nodes accumulate deficit only when all eligible candidates have deficit < cost (start of a round).
    - When a node is selected, its deficit is decremented by cost.
    - A node with deficit < cost cannot be selected in the current round, forcing the scheduler
      to give turns to other nodes.
    """

    def __init__(self, base_quantum: float = 1.0) -> None:
        self.base_quantum = base_quantum
        self._deficits: Dict[str, float] = {}

    def get_deficit(self, node_id: str) -> float:
        return round(self._deficits.get(node_id, 0.0), 3)

    def replenish_round(self, candidates: List[NodeProfile]) -> None:
        """Starts a new DRR round: adds adaptive quantum to all candidate nodes."""
        if not candidates:
            return

        scores = [n.effective_score for n in candidates]
        mean_score = max(0.01, float(np.mean(scores)))

        for node in candidates:
            current = self._deficits.get(node.id, 0.0)
            # Adaptive quantum: proportional to node's effective score relative to cluster average
            adaptive_quantum = self.base_quantum * (node.effective_score / mean_score)
            self._deficits[node.id] = current + adaptive_quantum

    def update_quantum_and_deficits(self, candidates: List[NodeProfile]) -> None:
        self.replenish_round(candidates)

    def get_eligible_with_deficit(self, candidates: List[NodeProfile], cost: float = 1.0) -> List[NodeProfile]:
        """Returns candidates that have accumulated at least `cost` deficit in the current round.
        If no candidate has sufficient deficit, a new round is triggered, replenishing all candidates.
        """
        if not candidates:
            return []

        # Find candidates with sufficient deficit
        eligible = [c for c in candidates if self._deficits.get(c.id, 0.0) >= cost]

        if not eligible:
            # Current round exhausted: replenish deficits for all candidates
            self.replenish_round(candidates)
            eligible = [c for c in candidates if self._deficits.get(c.id, 0.0) >= cost]

        return eligible or list(candidates)

    def deduct_cost(self, node_id: str, cost: float = 1.0) -> None:
        """Deducts execution cost from the selected node's deficit."""
        current = self._deficits.get(node_id, 0.0)
        self._deficits[node_id] = max(0.0, current - cost)

    def select_fair_node(self, candidates: List[NodeProfile], cost: float = 1.0) -> Optional[NodeProfile]:
        """Selects the candidate with the highest accumulated deficit meeting the cost."""
        eligible = self.get_eligible_with_deficit(candidates, cost=cost)
        if not eligible:
            return None

        # Pick candidate with highest deficit
        best = max(eligible, key=lambda c: self._deficits.get(c.id, 0.0))
        self.deduct_cost(best.id, cost=cost)
        return best


def calculate_fairness_cv(task_counts: List[int]) -> float:
    """Calculates Coefficient of Variation (CV = standard_deviation / mean).
    
    A lower CV indicates higher allocation equality across nodes.
    CV = 0.0 is perfect uniform distribution.
    """
    if not task_counts or len(task_counts) < 2:
        return 0.0
    arr = np.array(task_counts, dtype=np.float64)
    mean = float(np.mean(arr))
    if mean <= 0.0:
        return 0.0
    std = float(np.std(arr))
    return round(float(std / mean), 4)
