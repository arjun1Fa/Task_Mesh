"""Base capability scoring and EWMA dynamic performance multiplier."""

from taskmesh.core.models import NodeProfile


def compute_base_score(profile: NodeProfile) -> float:
    """Computes a static normalized base capability score from hardware specs."""
    caps = profile.capabilities
    # CPU score: normalized around 4 cores @ 2.5 GHz = 1.0
    cpu_factor = (caps.cpu_cores * (caps.cpu_frequency_mhz / 2500.0)) / 4.0

    # RAM score: normalized around 4GB (4096 MB) = 1.0
    ram_factor = caps.ram_total_mb / 4096.0

    # GPU score: 2.0x boost for dedicated GPU
    gpu_factor = 2.0 if caps.has_gpu else 0.5

    base = (0.4 * cpu_factor) + (0.3 * ram_factor) + (0.3 * gpu_factor)
    return max(0.1, round(base, 3))


class EWMAUpdater:
    """Updates node performance multiplier using Exponentially Weighted Moving Average (EWMA)."""

    def __init__(self, alpha: float = 0.2):
        self.alpha = max(0.01, min(1.0, alpha))

    def update_multiplier(
        self,
        current_multiplier: float,
        expected_duration_seconds: float,
        actual_duration_seconds: float,
    ) -> float:
        """Updates performance multiplier based on execution speed ratio.
        
        ratio > 1: Node completed faster than expected
        ratio < 1: Node completed slower than expected
        """
        if actual_duration_seconds <= 0.001:
            ratio = 2.0
        else:
            ratio = expected_duration_seconds / actual_duration_seconds

        # Clamp extreme ratios to prevent single-task divergence
        clamped_ratio = max(0.2, min(5.0, ratio))

        new_multiplier = (self.alpha * clamped_ratio) + ((1.0 - self.alpha) * current_multiplier)
        return max(0.1, min(10.0, round(new_multiplier, 4)))
