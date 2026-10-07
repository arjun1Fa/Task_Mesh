"""Baseline schedulers: Round Robin, Least Loaded, and Highest Bid."""

import asyncio
from typing import Dict, List

from taskmesh.core.enums import SchedulerMode
from taskmesh.core.errors import IneligibleNodeError
from taskmesh.core.models import NodeProfile, Task
from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.scheduler.base import filter_eligible_nodes
from taskmesh.scheduler.decision import SchedulerDecision


class RoundRobinScheduler:
    """Cyclically round-robins among eligible nodes."""

    def __init__(self) -> None:
        self._index: int = 0
        self._lock = asyncio.Lock()

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        async with self._lock:
            selected = eligible[self._index % len(eligible)]
            self._index = (self._index + 1) % len(eligible)

        return SchedulerDecision(
            task_id=task.id,
            selected_node_id=selected.id,
            policy_used=SchedulerMode.ROUND_ROBIN,
            candidate_node_ids=[n.id for n in eligible],
            candidate_scores={n.id: n.effective_score for n in eligible},
        )


class LeastLoadedScheduler:
    """Selects the eligible node with the lowest CPU/RAM load and active task count."""

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        def load_key(node: NodeProfile) -> float:
            if not node.telemetry:
                return 50.0
            return (
                node.telemetry.active_tasks * 20.0
                + node.telemetry.cpu_percent
                + node.telemetry.ram_percent
            )

        selected = min(eligible, key=load_key)

        return SchedulerDecision(
            task_id=task.id,
            selected_node_id=selected.id,
            policy_used=SchedulerMode.LEAST_LOADED,
            candidate_node_ids=[n.id for n in eligible],
            candidate_scores={n.id: n.effective_score for n in eligible},
        )


class HighestBidScheduler:
    """Selects the eligible node submitting the highest bid value."""

    def __init__(self, default_weights: Dict[str, float] = None) -> None:
        self.weights = default_weights or {
            "cpu": 0.2, "gpu": 0.2, "load": 0.2, "latency": 0.2, "reliability": 0.2
        }

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        bids = {n.id: calculate_node_bid(n, task, self.weights) for n in eligible}
        selected = max(eligible, key=lambda n: bids[n.id])

        return SchedulerDecision(
            task_id=task.id,
            selected_node_id=selected.id,
            policy_used=SchedulerMode.HIGHEST_BID,
            candidate_node_ids=[n.id for n in eligible],
            candidate_scores={n.id: n.effective_score for n in eligible},
            bids=bids,
        )
