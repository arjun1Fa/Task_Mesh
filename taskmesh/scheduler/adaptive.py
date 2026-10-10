"""TaskMesh Adaptive Scheduler combining scoring, DRR fairness, bidding, MWU, and Q-learning."""

import asyncio
from typing import Dict, List, Optional

from taskmesh.core.enums import OffloadPolicy, SchedulerMode
from taskmesh.core.errors import IneligibleNodeError
from taskmesh.core.models import NodeProfile, Task
from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.fairness.drr import DRRFairnessManager
from taskmesh.learning.mwu import MWUWeightLearner
from taskmesh.learning.qlearning import QLearningScheduler
from taskmesh.scheduler.base import filter_eligible_nodes
from taskmesh.scheduler.decision import SchedulerDecision
from taskmesh.scoring.base_score import EWMAUpdater, compute_base_score
from taskmesh.wireless.estimator import NetworkEstimator


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
        network_estimator: Optional[NetworkEstimator] = None,
    ) -> None:
        self.ewma = EWMAUpdater(alpha=ewma_alpha)
        self.drr = DRRFairnessManager(base_quantum=base_quantum)
        self.mwu = MWUWeightLearner(eta=mwu_eta)
        self.rl = QLearningScheduler(learning_rate=rl_lr, discount_factor=rl_gamma, epsilon=rl_epsilon)
        self.estimator = network_estimator or NetworkEstimator(alpha=ewma_alpha)
        self._lock = asyncio.Lock()

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        async with self._lock:
            # 1. DRR Fairness Gate: Filter eligible candidates that have sufficient deficit in the current round.
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

            fallback_reason: Optional[str] = None
            if rl_action < len(ranked_candidates):
                candidate_by_rl = ranked_candidates[rl_action]
            else:
                candidate_by_rl = top_candidate
                fallback_reason = "RL action out of bounds, defaulted to top bid"

            # 6. Wireless Network-Aware Cost & Local vs Remote Decision
            payload_size = 0
            if task.binary_meta:
                payload_size = task.binary_meta.payload_size_bytes
            elif isinstance(task.payload, dict) and "payload_size" in task.payload:
                payload_size = int(task.payload["payload_size"])

            local_candidate = next((n for n in eligible if n.capabilities.is_local), None)

            selected: NodeProfile
            local_estimate_ms: Optional[float] = None
            remote_estimate_ms: Optional[float] = None
            upload_ms: Optional[float] = None
            remote_inference_ms: Optional[float] = None
            download_ms: Optional[float] = None
            offload_decision: str = "remote"
            offload_reason: str = "remote execution selected"

            if task.offload_policy in (OffloadPolicy.LOCAL_ONLY, "local_only"):
                selected = local_candidate or candidate_by_rl
                offload_decision = "local"
                offload_reason = "task policy enforced local_only execution"
                local_estimate_ms = self.estimator.estimate_local_execution_time(task, selected, payload_size)
            elif candidate_by_rl.capabilities.is_local:
                selected = candidate_by_rl
                offload_decision = "local"
                offload_reason = "local node selected by adaptive bid and RL ranking"
                local_estimate_ms = self.estimator.estimate_local_execution_time(task, selected, payload_size)
            else:
                # Candidate is remote: evaluate remote execution breakdown
                remote_breakdown = self.estimator.estimate_remote_execution_time(task, candidate_by_rl, payload_size)
                remote_estimate_ms = remote_breakdown["total_remote_ms"]
                upload_ms = remote_breakdown["upload_ms"]
                remote_inference_ms = remote_breakdown["remote_inference_ms"]
                download_ms = remote_breakdown["download_ms"]

                if local_candidate is not None:
                    local_estimate_ms = self.estimator.estimate_local_execution_time(task, local_candidate, payload_size)
                    if local_estimate_ms <= remote_estimate_ms:
                        selected = local_candidate
                        offload_decision = "local"
                        offload_reason = f"local execution predicted faster or equal ({local_estimate_ms}ms <= {remote_estimate_ms}ms)"
                    else:
                        selected = candidate_by_rl
                        offload_decision = "remote"
                        offload_reason = f"remote execution predicted faster ({remote_estimate_ms}ms < {local_estimate_ms}ms)"
                else:
                    selected = candidate_by_rl
                    offload_decision = "remote"
                    offload_reason = "remote wireless execution selected (no local node available)"

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
                local_estimate_ms=local_estimate_ms,
                remote_estimate_ms=remote_estimate_ms,
                upload_ms=upload_ms,
                remote_inference_ms=remote_inference_ms,
                download_ms=download_ms,
                offload_decision=offload_decision,
                offload_reason=offload_reason,
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
