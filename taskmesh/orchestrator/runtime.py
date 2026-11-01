"""TaskMesh Orchestrator Runtime engine coordinating control plane and compute nodes."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
import websockets


from taskmesh.checkpoint.manager import CheckpointManager
from taskmesh.cluster.registry import NodeRegistry
from taskmesh.core.config import OrchestratorConfig
from taskmesh.core.enums import MessageType, NodeStatus, SchedulerMode, TaskStatus
from taskmesh.core.errors import DuplicateTaskError, IneligibleNodeError, TaskNotFoundError
from taskmesh.core.models import (
    CheckpointData,
    NodeProfile,
    Task,
    TaskCreate,
    TaskResult,
    utc_now,
)
from taskmesh.dlq.manager import DLQManager
from taskmesh.fairness.drr import calculate_fairness_cv
from taskmesh.idempotency.store import IdempotencyStore
from taskmesh.persistence.repositories import TaskRepository
from taskmesh.protocol.messages import (
    NodeDrainPayload,
    ProtocolMessage,
    TaskAssignmentPayload,
    TaskCancelPayload,
)
from taskmesh.queue.priority import PriorityQueue
from taskmesh.retry.runner import evaluate_retry
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.base import Scheduler
from taskmesh.scheduler.baseline import (
    HighestBidScheduler,
    LeastLoadedScheduler,
    RoundRobinScheduler,
)
from taskmesh.scheduler.decision import SchedulerDecision
from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.orchestrator.events import DashboardEventHub
from taskmesh.security.auth import AuthManager
from taskmesh.security.audit import AuditLogger
from taskmesh.security.hmac_auth import SecurityManager
from taskmesh.transport.binary_protocol import (
    create_binary_chunk_frame,
    split_into_chunks,
)
from taskmesh.transport.payload_store import BinaryPayloadStore
from taskmesh.wireless.estimator import NetworkEstimator

logger = logging.getLogger("taskmesh.runtime")


async def _send_websocket_text(ws: Any, text: str) -> None:
    """Sends text message across either FastAPI/Starlette WebSocket or client protocol."""
    if hasattr(ws, "send_text"):
        await ws.send_text(text)
    elif hasattr(ws, "send"):
        await ws.send(text)


async def _send_websocket_bytes(ws: Any, data: bytes) -> None:
    """Sends binary message frame across either FastAPI/Starlette WebSocket or client protocol."""
    if hasattr(ws, "send_bytes"):
        await ws.send_bytes(data)
    elif hasattr(ws, "send"):
        await ws.send(data)


class OrchestratorRuntime:
    """The central orchestration coordinator for TaskMesh."""

    def __init__(
        self,
        repository: TaskRepository,
        config: Optional[OrchestratorConfig] = None,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self.repo = repository
        self.registry = NodeRegistry()
        self.queue = PriorityQueue()
        self.idempotency = IdempotencyStore()
        self.dlq = DLQManager()
        self.checkpoints = CheckpointManager()
        self.security = SecurityManager(secret_key=self.config.join_token, secure_mode=self.config.secure_mode)
        self.payload_store = BinaryPayloadStore(max_payload_size_bytes=self.config.max_payload_size_bytes)
        self.network_estimator = NetworkEstimator(alpha=self.config.ewma_alpha)

        # Initialize scheduler based on mode
        self.scheduler: Scheduler = self._init_scheduler(self.config.scheduler_mode)
        if isinstance(self.scheduler, AdaptiveScheduler):
            self.scheduler.estimator = self.network_estimator

        # In-memory tracking for active scheduling decisions and explainability audit
        self._decisions: List[SchedulerDecision] = []
        self._delayed_tasks: List[Task] = []
        self._running_attempts: Dict[str, str] = {}  # task_id -> attempt_id

        # Master Controls, Events, Auth & Audit
        db_file = self.config.db_url.replace("sqlite:///", "") if self.config.db_url.startswith("sqlite:///") else "taskmesh.db"
        self.events = DashboardEventHub()
        self.audit = AuditLogger(db_path=db_file)
        self.auth = AuthManager(db_path=db_file)
        self._dispatch_paused: bool = False

        # Lifecycle control
        self.is_running = False
        self._background_tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()


    def _init_scheduler(self, mode: SchedulerMode) -> Scheduler:
        if mode == SchedulerMode.ROUND_ROBIN:
            return RoundRobinScheduler()
        elif mode == SchedulerMode.LEAST_LOADED:
            return LeastLoadedScheduler()
        elif mode == SchedulerMode.HIGHEST_BID:
            return HighestBidScheduler()
        else:
            return AdaptiveScheduler(
                ewma_alpha=self.config.ewma_alpha,
                mwu_eta=self.config.mwu_eta,
                rl_lr=self.config.rl_learning_rate,
                rl_gamma=self.config.rl_discount_factor,
                rl_epsilon=self.config.rl_epsilon,
            )

    async def start(self) -> None:
        """Starts the orchestrator engine and background loops."""
        self.is_running = True

        if self.config.standby_mode:
            logger.info(f"Starting TaskMesh Orchestrator in STANDBY mode (Replicating from {self.config.primary_url})")
            self._background_tasks = [
                asyncio.create_task(self._standby_replication_loop(), name="standby_replicator"),
            ]
            return

        logger.info(f"Starting TaskMesh Orchestrator (Mode: {self.config.scheduler_mode.value})")

        # Recover uncompleted tasks from persistence into queue
        running_tasks = await self.repo.list(status=TaskStatus.RUNNING, limit=500)
        pending_tasks = await self.repo.list(status=TaskStatus.PENDING, limit=500)
        for t in running_tasks + pending_tasks:
            t.status = TaskStatus.PENDING
            t.assigned_node_id = None
            t.active_lease = None
            await self.repo.save(t)
            await self.queue.enqueue(t)

        self._background_tasks = [
            asyncio.create_task(self._dispatch_loop(), name="dispatcher"),
            asyncio.create_task(self._health_monitor_loop(), name="health_monitor"),
            asyncio.create_task(self._lease_checker_loop(), name="lease_checker"),
            asyncio.create_task(self._delayed_tasks_loop(), name="delayed_scheduler"),
        ]

    async def create_snapshot(self) -> Dict[str, Any]:
        """Creates a complete state snapshot for standby replication."""
        tasks = await self.repo.list(limit=5000)
        nodes = await self.registry.list_nodes()
        checkpoints = list(self.checkpoints._checkpoints.values())

        mwu_w = {}
        q_tab = {}
        drr_def = {}
        if isinstance(self.scheduler, AdaptiveScheduler):
            mwu_w = self.scheduler.mwu.get_weights()
            q_tab = {str(k): v for k, v in self.scheduler.rl.q_table.items()}
            drr_def = dict(self.scheduler.drr._deficits)

        return {
            "timestamp": utc_now().isoformat(),
            "tasks": [t.model_dump(mode="json") for t in tasks],
            "nodes": [n.model_dump(mode="json") for n in nodes],
            "checkpoints": [c.model_dump(mode="json") for c in checkpoints],
            "mwu_weights": mwu_w,
            "q_table": q_tab,
            "drr_deficits": drr_def,
        }

    async def apply_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Applies a replicated snapshot into local state."""
        import ast
        for t_data in snapshot.get("tasks", []):
            t = Task.model_validate(t_data)
            await self.repo.save(t)

        for n_data in snapshot.get("nodes", []):
            n = NodeProfile.model_validate(n_data)
            self.registry._nodes[n.id] = n

        for c_data in snapshot.get("checkpoints", []):
            c = CheckpointData.model_validate(c_data)
            await self.checkpoints.save_checkpoint(c)

        if isinstance(self.scheduler, AdaptiveScheduler):
            if "mwu_weights" in snapshot and snapshot["mwu_weights"]:
                self.scheduler.mwu.weights = dict(snapshot["mwu_weights"])
            if "drr_deficits" in snapshot and snapshot["drr_deficits"]:
                self.scheduler.drr._deficits = {k: float(v) for k, v in snapshot["drr_deficits"].items()}
            if "q_table" in snapshot and snapshot["q_table"]:
                for k_str, q_vals in snapshot["q_table"].items():
                    try:
                        k_tuple = ast.literal_eval(k_str)
                        self.scheduler.rl.q_table[k_tuple] = [float(x) for x in q_vals]
                    except Exception:
                        pass

    async def promote_to_primary(self) -> None:
        """Promotes a standby orchestrator to primary upon primary failure."""
        async with self._lock:
            if not self.config.standby_mode:
                return
            logger.warning("Automated Failover: PROMOTING Standby Orchestrator to PRIMARY!")
            self.config.standby_mode = False

            # Recover tasks
            running = await self.repo.list(status=TaskStatus.RUNNING, limit=500)
            pending = await self.repo.list(status=TaskStatus.PENDING, limit=500)
            for t in running + pending:
                t.status = TaskStatus.PENDING
                t.assigned_node_id = None
                t.active_lease = None
                await self.repo.save(t)
                await self.queue.enqueue(t)

            self._background_tasks = [
                asyncio.create_task(self._dispatch_loop(), name="dispatcher"),
                asyncio.create_task(self._health_monitor_loop(), name="health_monitor"),
                asyncio.create_task(self._lease_checker_loop(), name="lease_checker"),
                asyncio.create_task(self._delayed_tasks_loop(), name="delayed_scheduler"),
            ]

    async def _standby_replication_loop(self) -> None:
        """Polls primary orchestrator snapshot endpoint and promotes upon failure."""
        import httpx
        consecutive_failures = 0
        max_failures_before_promotion = 3

        while self.is_running and self.config.standby_mode:
            try:
                if self.config.primary_url:
                    headers = {"Authorization": f"Bearer {self.config.join_token}"}
                    async with httpx.AsyncClient(timeout=2.0, headers=headers) as client:
                        resp = await client.get(f"{self.config.primary_url}/v1/standby/snapshot")
                        if resp.status_code == 200:
                            snapshot = resp.json()
                            await self.apply_snapshot(snapshot)
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
            except Exception as e:
                consecutive_failures += 1
                logger.warning(f"Standby health probe failed ({consecutive_failures}/{max_failures_before_promotion}): {e}")

            if consecutive_failures >= max_failures_before_promotion:
                logger.error(f"Primary orchestrator failure confirmed! Promoting to PRIMARY.")
                await self.promote_to_primary()
                break

            await asyncio.sleep(self.config.snapshot_interval_seconds)

    async def stop(self) -> None:
        """Gracefully stops the runtime."""
        self.is_running = False
        for t in self._background_tasks:
            t.cancel()
        logger.info("TaskMesh Orchestrator stopped cleanly")

    async def submit_task(self, create_req: TaskCreate, binary_data: Optional[bytes] = None) -> Task:
        """Submits a new task to the cluster."""
        # 1. Idempotency check
        if create_req.idempotency_key:
            existing_id = await self.idempotency.get(create_req.idempotency_key)
            if existing_id:
                existing_task = await self.repo.get(existing_id)
                if existing_task:
                    return existing_task

        # 2. Build task entity
        task = Task(
            task_type=create_req.task_type,
            payload=create_req.payload,
            priority=create_req.priority,
            idempotency_key=create_req.idempotency_key,
            scheduled_at=create_req.scheduled_at,
            repeat_every_seconds=create_req.repeat_every_seconds,
            timeout_seconds=create_req.timeout_seconds,
            requires_gpu=create_req.requires_gpu,
            required_memory_mb=create_req.required_memory_mb,
            required_capabilities=create_req.required_capabilities,
            preferred_capabilities=create_req.preferred_capabilities,
            retry_policy=create_req.retry_policy,
            supports_checkpoint=create_req.supports_checkpoint,
            offload_policy=create_req.offload_policy,
            binary_meta=create_req.binary_meta,
            metadata=create_req.metadata,
        )

        if binary_data:
            meta = await self.payload_store.add_payload(
                task_id=task.id,
                data=binary_data,
                workload_type=task.task_type,
                model_identifier=task.payload.get("model", "yolov8n"),
                mime_type=task.payload.get("mime_type", "image/jpeg"),
                chunk_size_bytes=self.config.chunk_size_bytes,
            )
            task.binary_meta = meta

        if task.idempotency_key:
            await self.idempotency.set_if_absent(task.idempotency_key, task.id)

        # 3. Schedule or enqueue
        now = utc_now()
        if task.scheduled_at and task.scheduled_at > now:
            task.status = TaskStatus.SCHEDULED
            async with self._lock:
                self._delayed_tasks.append(task)
        else:
            task.status = TaskStatus.PENDING
            await self.queue.enqueue(task)

        await self.repo.save(task)
        logger.info(f"Accepted task [{task.id}] type={task.task_type} priority={task.priority} offload_policy={task.offload_policy.value}")
        await self.events.broadcast(
            event_type="task.submitted",
            data={
                "task_id": task.id,
                "task_type": task.task_type,
                "priority": task.priority,
                "offload_policy": task.offload_policy.value,
                "has_binary_payload": task.binary_meta is not None,
            },
            entity_id=task.id,
        )
        return task


    async def cancel_task(self, task_id: str, reason: str = "Client requested cancellation") -> Task:
        task = await self.repo.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        if task.status.is_terminal():
            return task

        task.status = TaskStatus.CANCELLED
        task.error_message = reason
        await self.repo.save(task)

        # If currently running on a node, send cancellation over WebSocket
        if task.assigned_node_id:
            ws = await self.registry.get_socket(task.assigned_node_id)
            if ws:
                cancel_msg = ProtocolMessage(
                    message_type=MessageType.TASK_CANCEL,
                    node_id=task.assigned_node_id,
                    payload=TaskCancelPayload(task_id=task.id, attempt_id=task.current_attempt_id, reason=reason).model_dump(mode="json"),
                )
                try:
                    await _send_websocket_text(ws, json.dumps(cancel_msg.model_dump(mode="json")))
                except Exception as e:
                    logger.warning(f"Failed to transmit cancellation to node {task.assigned_node_id}: {e}")

        logger.info(f"Task [{task_id}] cancelled: {reason}")
        await self.events.broadcast(
            event_type="task.cancelled",
            data={"task_id": task_id, "reason": reason},
            entity_id=task_id,
        )
        return task

    async def retry_task(self, task_id: str) -> Task:
        task = await self.repo.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        task.status = TaskStatus.PENDING
        task.assigned_node_id = None
        task.active_lease = None
        task.retry_count = 0
        task.error_message = None
        await self.repo.save(task)
        await self.queue.enqueue(task)
        await self.events.broadcast(
            event_type="task.retried",
            data={"task_id": task_id},
            entity_id=task_id,
        )
        return task

    async def drain_node(self, node_id: str, actor: str = "system") -> None:
        await self.registry.set_draining(node_id)
        self.audit.log(action="node.drain", actor=actor, target=node_id, result="success")
        ws = await self.registry.get_socket(node_id)
        if ws:
            msg = ProtocolMessage(
                message_type=MessageType.NODE_DRAIN,
                node_id=node_id,
                payload=NodeDrainPayload(node_id=node_id).model_dump(mode="json"),
            )
            await _send_websocket_text(ws, json.dumps(msg.model_dump(mode="json")))
        await self.events.broadcast(
            event_type="node.drained",
            data={"node_id": node_id, "status": NodeStatus.DRAINING.value},
            entity_id=node_id,
        )

    async def get_decisions(self, limit: int = 50) -> List[SchedulerDecision]:
        async with self._lock:
            return list(self._decisions[-limit:])

    async def get_fairness_metric(self) -> float:
        nodes = await self.registry.list_nodes()
        counts = [n.total_completed for n in nodes]
        return calculate_fairness_cv(counts)

    # ---------------------------------------------------------
    # Master Controls & Cluster Management Operations
    # ---------------------------------------------------------

    async def set_dispatch_paused(self, paused: bool, actor: str = "system") -> None:
        """Pauses or resumes the orchestrator task dispatch loop."""
        self._dispatch_paused = paused
        action = "dispatch.pause" if paused else "dispatch.resume"
        self.audit.log(action=action, actor=actor, target="dispatcher", result="success")
        logger.info(f"Task dispatch {'PAUSED' if paused else 'RESUMED'} by {actor}")
        await self.events.broadcast(
            event_type="dispatch.state_changed",
            data={"paused": paused, "actor": actor},
            entity_id="dispatcher",
        )

    async def switch_scheduler_mode(self, mode: SchedulerMode, actor: str = "system") -> None:
        """Safely hot-swaps the active scheduler engine."""
        prev_mode = self.config.scheduler_mode
        self.scheduler = self._init_scheduler(mode)
        if isinstance(self.scheduler, AdaptiveScheduler):
            self.scheduler.estimator = self.network_estimator
        self.config.scheduler_mode = mode
        self.audit.log(
            action="scheduler.mode_changed",
            actor=actor,
            target=mode.value,
            result="success",
            details={"previous_mode": prev_mode.value, "new_mode": mode.value},
        )
        logger.info(f"Scheduler mode switched from {prev_mode.value} to {mode.value} by {actor}")
        await self.events.broadcast(
            event_type="scheduler.mode_changed",
            data={"previous_mode": prev_mode.value, "new_mode": mode.value, "actor": actor},
            entity_id="scheduler",
        )

    async def set_adaptive_toggles(self, toggles: Dict[str, bool], actor: str = "system") -> Dict[str, bool]:
        """Toggles individual adaptive stages within the AdaptiveScheduler."""
        if not isinstance(self.scheduler, AdaptiveScheduler):
            raise ValueError(f"Cannot configure adaptive toggles while in {self.config.scheduler_mode.value} mode")
        self.scheduler.set_toggles(toggles)
        current = self.scheduler.get_toggles()
        self.audit.log(
            action="scheduler.toggles_changed",
            actor=actor,
            target="adaptive_scheduler",
            result="success",
            details=current,
        )
        await self.events.broadcast(
            event_type="scheduler.toggles_changed",
            data=current,
            entity_id="scheduler",
        )
        return current

    async def resume_node(self, node_id: str, actor: str = "system") -> None:
        """Resumes a drained or maintenance node to online status."""
        await self.registry.set_resumed(node_id)
        self.audit.log(action="node.resume", actor=actor, target=node_id, result="success")
        logger.info(f"Node [{node_id}] resumed to ONLINE by {actor}")
        await self.events.broadcast(
            event_type="node.status_changed",
            data={"node_id": node_id, "status": NodeStatus.ONLINE.value, "actor": actor},
            entity_id=node_id,
        )

    async def set_node_maintenance(self, node_id: str, is_maint: bool = True, actor: str = "system") -> None:
        """Toggles maintenance mode for a node."""
        await self.registry.set_maintenance(node_id, is_maint=is_maint)
        status_val = NodeStatus.MAINTENANCE.value if is_maint else NodeStatus.ONLINE.value
        self.audit.log(action="node.maintenance", actor=actor, target=node_id, result="success", details={"maintenance": is_maint})
        logger.info(f"Node [{node_id}] maintenance set to {is_maint} by {actor}")
        await self.events.broadcast(
            event_type="node.status_changed",
            data={"node_id": node_id, "status": status_val, "actor": actor},
            entity_id=node_id,
        )

    async def remove_node(self, node_id: str, force: bool = False, actor: str = "system") -> bool:
        """Removes a registered node, ensuring active tasks are handled safely."""
        running = await self.repo.find_by_assigned_node(node_id, status=TaskStatus.RUNNING)
        if running and not force:
            raise ValueError(f"Cannot remove node [{node_id}]: {len(running)} active task(s) currently executing. Drain the node first or use force=True.")

        if running and force:
            logger.warning(f"Force removing node [{node_id}] with {len(running)} running tasks; re-queueing tasks.")
            await self._recover_tasks_for_failed_node(node_id)

        removed = await self.registry.remove_node(node_id)
        if removed:
            self.audit.log(action="node.remove", actor=actor, target=node_id, result="success", details={"forced": force})
            await self.events.broadcast(
                event_type="node.removed",
                data={"node_id": node_id, "forced": force, "actor": actor},
                entity_id=node_id,
            )
        return removed

    async def get_node_tasks(self, node_id: str, limit: int = 100) -> List[Task]:
        """Returns all tasks associated with a specific compute node."""
        running = await self.repo.find_by_assigned_node(node_id, status=TaskStatus.RUNNING)
        completed = await self.repo.find_by_assigned_node(node_id, status=TaskStatus.COMPLETED)
        failed = await self.repo.find_by_assigned_node(node_id, status=TaskStatus.FAILED)
        combined = running + completed + failed
        combined.sort(key=lambda t: t.created_at, reverse=True)
        return combined[:limit]

    async def get_scheduler_diagnostics(self) -> Dict[str, Any]:
        """Gathers a consistent, read-only explainability snapshot of the scheduler pipeline."""
        nodes = await self.registry.list_nodes()
        is_adaptive = isinstance(self.scheduler, AdaptiveScheduler)

        candidate_diagnostics = []
        dummy_task = Task(task_type="image_inference", payload={"model": "yolov8n"})
        weights = self.scheduler.mwu.get_weights() if is_adaptive else {"cpu": 0.2, "gpu": 0.2, "load": 0.2, "latency": 0.2, "reliability": 0.2}

        mean_score = 1.0
        if nodes:
            mean_score = max(0.01, sum(n.effective_score for n in nodes) / len(nodes))

        for n in nodes:
            deficit = self.scheduler.drr.get_deficit(n.id) if is_adaptive else 0.0
            adaptive_quantum = round(1.0 * (n.effective_score / mean_score), 3) if is_adaptive else 1.0
            bid_val = calculate_node_bid(n, dummy_task, weights)
            candidate_diagnostics.append({
                "node_id": n.id,
                "status": n.status.value,
                "base_score": n.base_score,
                "performance_multiplier": n.performance_multiplier,
                "effective_score": n.effective_score,
                "drr_deficit": deficit,
                "drr_quantum": adaptive_quantum,
                "drr_eligible": deficit >= 1.0,
                "calculated_bid": bid_val,
                "total_completed": n.total_completed,
                "total_failed": n.total_failed,
            })

        q_info = {
            "entries_count": len(self.scheduler.rl.q_table) if is_adaptive else 0,
            "epsilon": self.scheduler.rl.epsilon if is_adaptive else 0.0,
            "learning_rate": self.scheduler.rl.lr if is_adaptive else 0.1,
            "discount_factor": self.scheduler.rl.gamma if is_adaptive else 0.9,
            "actions": ["Slot 0: Top Rank", "Slot 1: Second Rank", "Slot 2: Third Rank"],
            "state_space": "3x3x3 discretized tuples: (score_bucket [0,1,2], load_bucket [0,1,2], priority_bucket [0,1,2]) = 27 states",
            "sample_table": {str(k): v for k, v in list(self.scheduler.rl.q_table.items())[:12]} if is_adaptive else {},
        }

        wireless_info = {
            "per_node": {
                nid: m.model_dump(mode="json")
                for nid, m in self.network_estimator._metrics.items()
            },
            "formula": "T_remote = T_upload + T_rtt + T_queue + T_infer + T_download vs T_local = T_queue + T_infer",
            "baselines_ms": {"gpu_ai": 28.0, "cpu_ai": 135.0, "generic": 50.0},
            "queue_factor_ms": 25.0,
        }

        recent_decisions = [d.model_dump(mode="json") for d in self._decisions[-25:]]

        return {
            "mode": self.config.scheduler_mode.value,
            "dispatch_paused": self._dispatch_paused,
            "fairness_cv": await self.get_fairness_metric(),
            "adaptive_toggles": self.scheduler.get_toggles() if is_adaptive else None,
            "mwu": {
                "weights": weights,
                "eta": self.scheduler.mwu.eta if is_adaptive else 0.1,
                "formula": "w_k(t+1) = w_k(t) * exp(-eta * loss_k), then normalized",
            },
            "q_learning": q_info,
            "drr": {
                "base_quantum": 1.0,
                "scheduling_cost": 1.0,
                "mean_effective_score": round(mean_score, 3),
            },
            "candidates": candidate_diagnostics,
            "wireless_estimator": wireless_info,
            "recent_decisions": recent_decisions,
        }

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Provides in-depth system health across all internal components."""
        nodes = await self.registry.list_nodes()
        online_nodes = [n for n in nodes if n.status == NodeStatus.ONLINE]
        degraded_nodes = [n for n in nodes if n.status == NodeStatus.DEGRADED]
        draining_nodes = [n for n in nodes if n.status == NodeStatus.DRAINING]
        offline_nodes = [n for n in nodes if n.status == NodeStatus.OFFLINE]

        tasks = await self.repo.list(limit=2000)
        running = [t for t in tasks if t.status == TaskStatus.RUNNING]
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        dlq_items = await self.dlq.list_items()

        # Database health check
        db_healthy = True
        try:
            await self.repo.list(limit=1)
        except Exception:
            db_healthy = False

        status_str = "healthy"
        if not online_nodes:
            status_str = "no_online_nodes"
        elif len(dlq_items) > 10:
            status_str = "elevated_dlq"
        elif not db_healthy:
            status_str = "database_error"

        return {
            "status": status_str,
            "dispatch_paused": self._dispatch_paused,
            "scheduler_mode": self.config.scheduler_mode.value,
            "nodes": {
                "total": len(nodes),
                "online": len(online_nodes),
                "degraded": len(degraded_nodes),
                "draining": len(draining_nodes),
                "offline": len(offline_nodes),
            },
            "tasks": {
                "total": len(tasks),
                "running": len(running),
                "pending": len(pending),
                "dlq": len(dlq_items),
                "priority_queue_size": self.queue.size,
            },
            "components": {
                "database": "operational" if db_healthy else "degraded",
                "priority_queue": "operational",
                "binary_payload_store": f"{len(self.payload_store._store)} in-memory payloads",
                "checkpoint_manager": f"{len(self.checkpoints._checkpoints)} checkpoints",
                "idempotency_store": f"{len(self.idempotency._entries)} keys",
                "standby_replication": "standby" if self.config.standby_mode else "primary",
            },
            "timestamp": utc_now().isoformat(),
        }

    async def update_system_config(self, updates: Dict[str, Any], actor: str = "system") -> Dict[str, Any]:
        """Applies dynamic updates to permitted system configuration options."""
        allowed_keys = {
            "heartbeat_interval_seconds",
            "node_timeout_seconds",
            "task_lease_seconds",
            "scheduler_poll_seconds",
            "ewma_alpha",
            "mwu_eta",
            "rl_epsilon",
        }
        modified = {}
        for k, v in updates.items():
            if k in allowed_keys and hasattr(self.config, k):
                try:
                    val = float(v)
                    setattr(self.config, k, val)
                    modified[k] = val
                except (ValueError, TypeError):
                    pass

        self.audit.log(
            action="system.config_updated",
            actor=actor,
            target="system_config",
            result="success",
            details=modified,
        )
        await self.events.broadcast(
            event_type="config.updated",
            data=modified,
            entity_id="system_config",
        )
        return modified

    # ---------------------------------------------------------
    # Core Dispatch Loop
    # ---------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        while self.is_running:
            try:
                if self._dispatch_paused:
                    await asyncio.sleep(0.5)
                    continue

                task = await self.queue.dequeue(timeout_seconds=0.5)
                if not task:
                    await asyncio.sleep(self.config.scheduler_poll_seconds)
                    continue

                # Refresh task from repo in case it was cancelled while in queue
                latest = await self.repo.get(task.id)
                if not latest or latest.status.is_terminal():
                    continue
                task = latest

                nodes = await self.registry.list_nodes(status=NodeStatus.ONLINE)
                if not nodes:
                    # No nodes available yet, re-enqueue and wait
                    await self.queue.enqueue(task)
                    await asyncio.sleep(1.0)
                    continue

                try:
                    decision = await self.scheduler.select_node(task, nodes)
                except IneligibleNodeError:
                    # No nodes currently meet task requirements, wait and re-enqueue
                    await self.queue.enqueue(task)
                    await asyncio.sleep(1.0)
                    continue

                selected_node_id = decision.selected_node_id
                ws = await self.registry.get_socket(selected_node_id)
                if not ws:
                    # Node connection dropped before dispatch
                    await self.queue.enqueue(task)
                    continue

                # Attach latest checkpoint if resuming
                latest_cp = await self.checkpoints.get_latest_checkpoint(task.id)
                cp_state = latest_cp.state if latest_cp else None

                # Advance task attempt and assign lease
                attempt_id = task.next_attempt(selected_node_id, self.config.task_lease_seconds)
                await self.repo.save(task)

                # Record decision
                async with self._lock:
                    self._decisions.append(decision)
                    self._running_attempts[task.id] = attempt_id

                # Build TaskAssignment message
                payload_dict = dict(task.payload)
                if task.binary_meta:
                    payload_dict["has_binary_payload"] = True
                    payload_dict["binary_meta"] = task.binary_meta.model_dump(mode="json")

                assignment = TaskAssignmentPayload(
                    task_id=task.id,
                    attempt_id=attempt_id,
                    lease_id=task.active_lease.lease_id if task.active_lease else "lease",
                    lease_expires_at=task.active_lease.expires_at if task.active_lease else utc_now(),
                    task_type=task.task_type,
                    payload=payload_dict,
                    priority=task.priority,
                    timeout_seconds=task.timeout_seconds,
                    checkpoint_state=cp_state,
                )
                msg = ProtocolMessage(
                    message_type=MessageType.TASK_ASSIGNMENT,
                    node_id=selected_node_id,
                    payload=assignment.model_dump(mode="json"),
                )
                self.security.sign(msg)
                await _send_websocket_text(ws, json.dumps(msg.model_dump(mode="json")))

                # Transmit binary payload chunks over WebSocket binary frames if present
                if task.binary_meta:
                    raw_bytes = await self.payload_store.get_payload(task.id)
                    if raw_bytes is not None:
                        start_upload = time.perf_counter()
                        chunks = split_into_chunks(raw_bytes, chunk_size=self.config.chunk_size_bytes)
                        for chunk_idx, chunk in enumerate(chunks):
                            frame = create_binary_chunk_frame(task.id, chunk_idx, len(chunks), chunk)
                            await _send_websocket_bytes(ws, frame)
                        upload_duration = time.perf_counter() - start_upload
                        is_loc = getattr(decision, "offload_decision", "remote") == "local"
                        self.network_estimator.update_transfer(
                            selected_node_id,
                            len(raw_bytes),
                            upload_duration,
                            direction="upload",
                            is_local=is_loc,
                        )

                logger.info(f"Dispatched task [{task.id}] attempt [{attempt_id}] to node [{selected_node_id}] via {decision.policy_used.value}")
                await self.events.broadcast(
                    event_type="task.assigned",
                    data={
                        "task_id": task.id,
                        "task_type": task.task_type,
                        "selected_node_id": selected_node_id,
                        "attempt_id": attempt_id,
                        "priority": task.priority,
                        "policy_used": decision.policy_used.value,
                        "candidate_scores": decision.candidate_scores,
                        "bids": decision.bids,
                        "offload_decision": getattr(decision, "offload_decision", "remote"),
                        "offload_reason": getattr(decision, "offload_reason", ""),
                    },
                    entity_id=task.id,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dispatch loop: {e}", exc_info=True)
                await asyncio.sleep(0.5)

    # ---------------------------------------------------------
    # Node Protocol Message Processing
    # ---------------------------------------------------------

    async def handle_node_message(self, ws: websockets.WebSocketServerProtocol, raw_data: str) -> None:
        """Processes incoming WebSocket protocol messages from compute nodes."""
        data = json.loads(raw_data)
        msg = ProtocolMessage.model_validate(data)

        # Validate security integrity & replay
        is_valid, sec_err = self.security.validate_incoming(msg)
        if not is_valid:
            logger.warning(f"Rejected message from node [{msg.node_id}]: {sec_err}")
            return
        node_id = msg.node_id or ""

        if msg.message_type == MessageType.PING:
            pong = ProtocolMessage(
                message_type=MessageType.PONG,
                node_id=node_id,
                payload={"orig_timestamp": msg.timestamp.isoformat()},
            )
            self.security.sign(pong)
            await _send_websocket_text(ws, json.dumps(pong.model_dump(mode="json")))

        elif msg.message_type == MessageType.HEARTBEAT:
            await self.registry.update_heartbeat(node_id)
            # Estimate RTT from heartbeat timestamp
            now = utc_now()
            rtt_ms = (now - msg.timestamp).total_seconds() * 1000.0
            if 0.0 < rtt_ms < 5000.0:
                self.network_estimator.update_rtt(node_id, rtt_ms)

        elif msg.message_type == MessageType.TELEMETRY:
            telem_raw = msg.payload.get("telemetry")
            if telem_raw:
                from taskmesh.core.models import NodeTelemetry
                telem = NodeTelemetry.model_validate(telem_raw)
                await self.registry.update_telemetry(node_id, telem)
                if telem.rtt_ms_ewma > 0:
                    self.network_estimator.update_rtt(node_id, telem.rtt_ms_ewma)
                if telem.upload_mbps_ewma > 0:
                    m = self.network_estimator.get_or_create_metrics(node_id)
                    m.upload_mbps_ewma = telem.upload_mbps_ewma
                if telem.download_mbps_ewma > 0:
                    m = self.network_estimator.get_or_create_metrics(node_id)
                    m.download_mbps_ewma = telem.download_mbps_ewma


        elif msg.message_type == MessageType.TASK_ACCEPTED:
            logger.debug(f"Node [{node_id}] accepted task [{msg.payload.get('task_id')}]")

        elif msg.message_type == MessageType.TASK_STARTED:
            task_id = msg.payload.get("task_id")
            if task_id:
                task = await self.repo.get(task_id)
                if task and task.status == TaskStatus.RUNNING:
                    task.updated_at = utc_now()
                    await self.repo.save(task)
                    await self.events.broadcast(
                        event_type="task.started",
                        data={"task_id": task_id, "node_id": node_id, "attempt_id": msg.payload.get("attempt_id")},
                        entity_id=task_id,
                    )

        elif msg.message_type == MessageType.TASK_PROGRESS:
            task_id = msg.payload.get("task_id")
            pct = float(msg.payload.get("progress", 0.0))
            if task_id:
                task = await self.repo.get(task_id)
                if task:
                    task.progress = pct
                    await self.repo.save(task)
                    await self.events.broadcast(
                        event_type="task.progress",
                        data={"task_id": task_id, "progress": pct, "node_id": node_id},
                        entity_id=task_id,
                    )

        elif msg.message_type == MessageType.TASK_CHECKPOINT:
            task_id = msg.payload.get("task_id")
            cp_raw = msg.payload.get("checkpoint")
            if task_id and cp_raw:
                cp = CheckpointData.model_validate(cp_raw)
                await self.checkpoints.save_checkpoint(cp)
                task = await self.repo.get(task_id)
                if task:
                    task.latest_checkpoint = cp
                    await self.repo.save(task)
                logger.debug(f"Saved checkpoint for task [{task_id}] step={cp.step}")

        elif msg.message_type == MessageType.TASK_COMPLETED:
            await self._process_task_completed(msg)

        elif msg.message_type == MessageType.TASK_FAILED:
            await self._process_task_failed(msg)

        elif msg.message_type == MessageType.TASK_REJECTED:
            task_id = msg.payload.get("task_id")
            if task_id:
                logger.warning(f"Node [{node_id}] rejected task [{task_id}], re-queueing")
                task = await self.repo.get(task_id)
                if task and not task.status.is_terminal():
                    task.status = TaskStatus.PENDING
                    task.assigned_node_id = None
                    task.active_lease = None
                    await self.repo.save(task)
                    await self.queue.enqueue(task)

    async def _process_task_completed(self, msg: ProtocolMessage) -> None:
        task_id = msg.payload.get("task_id")
        attempt_id = msg.payload.get("attempt_id")
        node_id = msg.node_id or ""
        result_raw = msg.payload.get("result")

        if not task_id or not result_raw:
            return

        task = await self.repo.get(task_id)
        if not task or task.status.is_terminal():
            return

        # Stale attempt validation
        if task.current_attempt_id and task.current_attempt_id != attempt_id:
            logger.warning(f"Discarding stale completed result for task [{task_id}] attempt [{attempt_id}]")
            return

        res = TaskResult.model_validate(result_raw)
        task.status = TaskStatus.COMPLETED
        task.result = res
        task.progress = 1.0
        task.active_lease = None
        task.assigned_node_id = node_id
        await self.repo.save(task)

        # Update node statistics
        node = await self.registry.get_node(node_id)
        if node:
            node.total_completed += 1
            if isinstance(self.scheduler, AdaptiveScheduler):
                # Fetch recent decision
                decision = next((d for d in reversed(self._decisions) if d.task_id == task_id), None)
                await self.scheduler.record_task_outcome(
                    node=node,
                    task=task,
                    decision=decision,
                    actual_duration_seconds=res.execution_time_seconds,
                    success=True,
                )

        logger.info(f"Task [{task_id}] successfully COMPLETED by node [{node_id}] in {res.execution_time_seconds}s")
        await self.events.broadcast(
            event_type="task.completed",
            data={
                "task_id": task_id,
                "attempt_id": attempt_id,
                "node_id": node_id,
                "execution_time_seconds": res.execution_time_seconds,
                "output": res.output,
                "metrics": res.metrics,
            },
            entity_id=task_id,
        )

        # Handle recurring task
        if task.repeat_every_seconds and task.repeat_every_seconds > 0:
            next_run = datetime.fromtimestamp(utc_now().timestamp() + task.repeat_every_seconds, timezone.utc)
            recurring_task = Task(
                task_type=task.task_type,
                payload=task.payload,
                priority=task.priority,
                scheduled_at=next_run,
                repeat_every_seconds=task.repeat_every_seconds,
                timeout_seconds=task.timeout_seconds,
                requires_gpu=task.requires_gpu,
                retry_policy=task.retry_policy,
                supports_checkpoint=task.supports_checkpoint,
            )
            recurring_task.status = TaskStatus.SCHEDULED
            async with self._lock:
                self._delayed_tasks.append(recurring_task)
            await self.repo.save(recurring_task)
            logger.info(f"Scheduled recurring task [{recurring_task.id}] next run at {next_run}")

    async def _process_task_failed(self, msg: ProtocolMessage) -> None:
        task_id = msg.payload.get("task_id")
        attempt_id = msg.payload.get("attempt_id")
        node_id = msg.node_id or ""
        error = msg.payload.get("error", "Unknown error")
        duration = float(msg.payload.get("execution_time_seconds", 0.0))

        if not task_id:
            return

        task = await self.repo.get(task_id)
        if not task or task.status.is_terminal():
            return

        # Stale attempt validation
        if task.current_attempt_id and task.current_attempt_id != attempt_id:
            return

        node = await self.registry.get_node(node_id)
        if node:
            node.total_failed += 1
            if isinstance(self.scheduler, AdaptiveScheduler):
                decision = next((d for d in reversed(self._decisions) if d.task_id == task_id), None)
                await self.scheduler.record_task_outcome(
                    node=node,
                    task=task,
                    decision=decision,
                    actual_duration_seconds=duration,
                    success=False,
                )

        # Retry logic evaluation
        decision = evaluate_retry(task, error)
        if decision.should_retry:
            task.retry_count = decision.attempt
            task.status = TaskStatus.RETRYING
            task.error_message = error
            task.assigned_node_id = None
            task.active_lease = None
            await self.repo.save(task)
            logger.warning(f"Task [{task_id}] failed on [{node_id}]: {error}. Retrying in {decision.delay_seconds:.2f}s (Attempt {decision.attempt})")

            async def delayed_requeue(t: Task, delay: float) -> None:
                await asyncio.sleep(delay)
                t.status = TaskStatus.PENDING
                await self.repo.save(t)
                await self.queue.enqueue(t)

            asyncio.create_task(delayed_requeue(task, decision.delay_seconds))
            await self.events.broadcast(
                event_type="task.retrying",
                data={
                    "task_id": task_id,
                    "node_id": node_id,
                    "error": error,
                    "attempt": decision.attempt,
                    "delay_seconds": decision.delay_seconds,
                },
                entity_id=task_id,
            )
        else:
            # Retries exhausted -> Move to Dead-Letter Queue (DLQ)
            logger.error(f"Task [{task_id}] permanently failed after retries. Moving to DLQ: {decision.reason}")
            await self.dlq.add(task, final_error=decision.reason)
            await self.repo.save(task)
            await self.events.broadcast(
                event_type="task.failed",
                data={
                    "task_id": task_id,
                    "node_id": node_id,
                    "error": decision.reason,
                    "moved_to_dlq": True,
                },
                entity_id=task_id,
            )

    # ---------------------------------------------------------
    # Health Monitoring & Fault Recovery Loops
    # ---------------------------------------------------------

    async def _health_monitor_loop(self) -> None:
        """Detects node heartbeat timeout, marks nodes OFFLINE, and recovers unfinished tasks."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval_seconds)
                now = utc_now()
                nodes = await self.registry.list_nodes()

                for node in nodes:
                    if node.status in (NodeStatus.ONLINE, NodeStatus.DEGRADED):
                        elapsed = (now - node.last_heartbeat).total_seconds()
                        if elapsed > self.config.node_timeout_seconds:
                            logger.error(f"Node [{node.id}] heartbeat timed out ({elapsed:.1f}s > {self.config.node_timeout_seconds}s). Marking OFFLINE.")
                            await self.registry.mark_offline(node.id)
                            await self._recover_tasks_for_failed_node(node.id)
                            await self.events.broadcast(
                                event_type="node.status_changed",
                                data={"node_id": node.id, "status": NodeStatus.OFFLINE.value, "reason": "Heartbeat timeout"},
                                entity_id=node.id,
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}", exc_info=True)

    async def _recover_tasks_for_failed_node(self, failed_node_id: str) -> None:
        """Recovers and reassigns tasks that were running on a failed node."""
        active_tasks = await self.repo.find_by_assigned_node(failed_node_id, status=TaskStatus.RUNNING)
        if not active_tasks:
            return

        logger.warning(f"Recovering {len(active_tasks)} active task(s) from failed node [{failed_node_id}]")
        for task in active_tasks:
            task.assigned_node_id = None
            task.active_lease = None
            task.error_message = f"Node [{failed_node_id}] failed while executing task"

            # Check if checkpoint exists
            cp = await self.checkpoints.get_latest_checkpoint(task.id)
            if cp:
                task.latest_checkpoint = cp
                logger.info(f"Task [{task.id}] resuming from checkpoint step={cp.step}")

            # Re-enqueue
            task.status = TaskStatus.PENDING
            await self.repo.save(task)
            await self.queue.enqueue(task)

    async def _lease_checker_loop(self) -> None:
        """Detects expired task leases and reassigns stuck tasks."""
        while self.is_running:
            try:
                await asyncio.sleep(5.0)
                expired = await self.repo.find_expired_leases()
                for task in expired:
                    logger.warning(f"Task [{task.id}] lease expired on node [{task.assigned_node_id}]. Re-queueing.")
                    task.assigned_node_id = None
                    task.active_lease = None
                    task.status = TaskStatus.PENDING
                    await self.repo.save(task)
                    await self.queue.enqueue(task)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error checking leases: {e}", exc_info=True)

    async def _delayed_tasks_loop(self) -> None:
        """Pushes scheduled future tasks into priority queue when due."""
        while self.is_running:
            try:
                await asyncio.sleep(0.5)
                now = utc_now()
                due = []
                async with self._lock:
                    remaining = []
                    for t in self._delayed_tasks:
                        if t.scheduled_at and t.scheduled_at <= now:
                            due.append(t)
                        else:
                            remaining.append(t)
                    self._delayed_tasks = remaining

                for task in due:
                    task.status = TaskStatus.PENDING
                    await self.repo.save(task)
                    await self.queue.enqueue(task)
                    logger.info(f"Scheduled task [{task.id}] is now due and queued")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in delayed scheduler: {e}", exc_info=True)
