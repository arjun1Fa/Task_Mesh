"""Multiplicative Weight Update (MWU / Hedge) for adaptive bidding factor weights."""

from typing import Dict, List
import numpy as np


class MWUWeightLearner:
    """Online weight adapter using Multiplicative Weight Update (MWU/Hedge).
    
    Dynamically balances factor weights (CPU, GPU, Load, Latency, Reliability)
    based on task execution outcome losses.
    """

    FACTOR_NAMES = ["cpu", "gpu", "load", "latency", "reliability"]

    def __init__(self, eta: float = 0.1) -> None:
        self.eta = eta
        # Initialize uniform weights summing to 1.0
        n = len(self.FACTOR_NAMES)
        self.weights: Dict[str, float] = {k: 1.0 / n for k in self.FACTOR_NAMES}

    def get_weights(self) -> Dict[str, float]:
        return dict(self.weights)

    def update(self, factor_losses: Dict[str, float]) -> Dict[str, float]:
        """Updates weights given bounded loss in [0, 1] for each factor.
        
        w_k(t+1) = w_k(t) * exp(-eta * loss_k)
        """
        new_w = {}
        for k in self.FACTOR_NAMES:
            loss = max(0.0, min(1.0, factor_losses.get(k, 0.5)))
            current = self.weights[k]
            new_w[k] = current * float(np.exp(-self.eta * loss))

        # Normalize weights so sum equals 1.0
        total = sum(new_w.values())
        if total > 0:
            for k in self.FACTOR_NAMES:
                self.weights[k] = round(new_w[k] / total, 4)

        return self.get_weights()
