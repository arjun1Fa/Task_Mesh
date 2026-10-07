"""TaskMesh Adaptive Scheduler combining scoring, DRR fairness, bidding, MWU, and Q-learning."""

import asyncio
from typing import Dict, List, Optional

from taskmesh.core.enums import SchedulerMode
from taskmesh.core.errors import IneligibleNodeError
from taskmesh.core.models import NodeProfile, Task
from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.fairness.drr import DRRFairnessManager
from taskmesh.learning.mwu import MWUWeightLearner
from taskmesh.learning.qlearning import QLearningScheduler
from taskmesh.scheduler.base import filter_eligible_nodes
from taskmesh.scheduler.decision import SchedulerDecision
from taskmesh.scoring.base_score import EWMAUpdater, compute_base_score


class AdaptiveScheduler:
    """The central TaskMesh adaptive multi-stage scheduler."""

    def __init__(
        self,
        ewma_alpha: float = 0.2,
        mwu_eta: float = 0.1,
        rl_lr: float = 0.1,
        rl_gamma: float = 0.9,
        rl_epsilon: float = 0.15,
        base_quantum: float = 1.0,
    ) -> None:
        self.ewma = EWMAUpdater(alpha=ewma_alpha)
        self.drr = DRRFairnessManager(base_quantum=base_quantum)
        self.mwu = MWUWeightLearner(eta=mwu_eta)
        self.rl = QLearningScheduler(learning_rate=rl_lr, discount_factor=rl_gamma, epsilon=rl_epsilon)
        self._lock = asyncio.Lock()

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        async with self._lock:
            # 1. DRR Fairness Gate: Filter eligible candidates that have sufficient deficit in the current round.
            # If all candidates have exhausted deficit, a new round is triggered, replenishing all candidate deficits.
            fair_candidates = self.drr.get_eligible_with_deficit(eligible, cost=1.0)

            # 2. Compute bids for fair candidates using current MWU weights
            current_weights = self.mwu.get_weights()
            bids = {n.id: calculate_node_bid(n, task, current_weights) for n in fair_candidates}

            # 3. Sort candidates by bid descending (ranking order)
            ranked_candidates = sorted(fair_candidates, key=lambda n: bids[n.id], reverse=True)
            top_candidate = ranked_candidates[0]

            # 4. Formulate discretized RL state
            rl_state = self.rl.discretize_state(top_candidate, task)

            # 5. RL action selection (slot index 0, 1, 2)
            rl_action = self.rl.select_action(rl_state, num_candidates=len(ranked_candidates))

            selected: NodeProfile
            fallback_reason: Optional[str] = None

            # 6. Apply selected candidate slot
            if rl_action < len(ranked_candidates):
                selected = ranked_candidates[rl_action]
            else:
                selected = top_candidate
                fallback_reason = "RL action out of bounds, defaulted to top bid"

            # 7. Deduct 1.0 execution cost from the selected node's DRR deficit
            self.drr.deduct_cost(selected.id, cost=1.0)

            # Record candidate stats for decision object
            scores = {n.id: n.effective_score for n in eligible}
            deficits = {n.id: self.drr.get_deficit(n.id) for n in eligible}

            return SchedulerDecision(
                task_id=task.id,
                selected_node_id=selected.id,
                policy_used=SchedulerMode.ADAPTIVE,
                candidate_node_ids=[n.id for n in fair_candidates],
                candidate_scores=scores,
                bids=bids,
                fairness_deficits=deficits,
                rl_state=rl_state,
                rl_action=rl_action,
                fallback_reason=fallback_reason,
            )

    async def record_task_outcome(
        self,
        node: NodeProfile,
        task: Task,
        decision: Optional[SchedulerDecision],
        actual_duration_seconds: float,
        success: bool,
    ) -> None:
        """Feedback loop: updates EWMA multiplier, MWU weights, and Q-table."""
        async with self._lock:
            # 1. Update node EWMA multiplier
            expected_time = max(0.1, task.timeout_seconds * 0.2)
            node.performance_multiplier = self.ewma.update_multiplier(
                node.performance_multiplier,
                expected_duration_seconds=expected_time,
                actual_duration_seconds=actual_duration_seconds,
            )

            # 2. Update MWU weights based on outcome losses
            time_loss = min(1.0, actual_duration_seconds / max(1.0, task.timeout_seconds))
            status_loss = 0.0 if success else 1.0

            losses = {
                "cpu": 0.5 * time_loss,
                "gpu": 0.8 * status_loss if task.requires_gpu else 0.2,
                "load": time_loss,
                "latency": min(1.0, (node.telemetry.network_latency_ms if node.telemetry else 10.0) / 100.0),
                "reliability": status_loss,
            }
            self.mwu.update(losses)

            # 3. Update Q-learning table
            if decision and decision.rl_state is not None and decision.rl_action is not None:
                reward = self.rl.calculate_reward(
                    success=success,
                    execution_time=actual_duration_seconds,
                    timeout_seconds=task.timeout_seconds,
                )
                self.rl.update(
                    state=decision.rl_state,
                    action=decision.rl_action,
                    reward=reward,
                    next_state=None,
                )
