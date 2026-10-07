"""Deficit Round Robin (DRR) with adaptive quantum for multi-node fairness."""

from typing import Dict, List, Optional
import numpy as np

from taskmesh.core.models import NodeProfile, Task


class DRRFairnessManager:
    """Fairness controller using Deficit Round Robin with adaptive quantum.
    
    Prevents node starvation while allowing higher-capacity nodes to carry proportional load.
    """

    def __init__(self, base_quantum: float = 1.0) -> None:
        self.base_quantum = base_quantum
        self._deficits: Dict[str, float] = {}

    def get_deficit(self, node_id: str) -> float:
        return self._deficits.get(node_id, 0.0)

    def update_quantum_and_deficits(self, nodes: List[NodeProfile]) -> None:
        """Adds adaptive quantum to all candidate nodes based on effective score."""
        if not nodes:
            return

        scores = [n.effective_score for n in nodes]
        mean_score = max(0.01, float(np.mean(scores)))

        for node in nodes:
            current = self._deficits.get(node.id, 0.0)
            # Adaptive quantum: proportional to node's effective score relative to cluster average
            adaptive_quantum = self.base_quantum * (node.effective_score / mean_score)
            self._deficits[node.id] = current + adaptive_quantum

    def select_fair_node(self, candidates: List[NodeProfile], cost: float = 1.0) -> Optional[NodeProfile]:
        """Selects the candidate with the highest accumulated deficit meeting the cost."""
        if not candidates:
            return None

        # Filter candidates that have enough deficit
        eligible = [c for c in candidates if self._deficits.get(c.id, 0.0) >= cost]

        if not eligible:
            # Replenish deficits once
            self.update_quantum_and_deficits(candidates)
            eligible = [c for c in candidates if self._deficits.get(c.id, 0.0) >= cost]

        if not eligible:
            # Fallback to candidate with maximum deficit
            best = max(candidates, key=lambda c: self._deficits.get(c.id, 0.0))
        else:
            best = max(eligible, key=lambda c: self._deficits.get(c.id, 0.0))

        # Deduct cost
        self._deficits[best.id] = max(0.0, self._deficits.get(best.id, 0.0) - cost)
        return best


def calculate_fairness_cv(task_counts: List[int]) -> float:
    """Calculates Coefficient of Variation (CV = standard_deviation / mean).
    
    A lower CV indicates higher allocation equality across nodes.
    """
    if not task_counts or len(task_counts) < 2:
        return 0.0
    arr = np.array(task_counts, dtype=np.float64)
    mean = float(np.mean(arr))
    if mean <= 0.0:
        return 0.0
    std = float(np.std(arr))
    return round(float(std / mean), 4)
