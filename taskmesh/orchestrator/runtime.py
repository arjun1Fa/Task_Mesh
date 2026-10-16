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
                    async with httpx.AsyncClient(timeout=2.0) as client:
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
        return task

    async def drain_node(self, node_id: str) -> None:
        await self.registry.set_draining(node_id)
        ws = await self.registry.get_socket(node_id)
        if ws:
            msg = ProtocolMessage(
                message_type=MessageType.NODE_DRAIN,
                node_id=node_id,
                payload=NodeDrainPayload(node_id=node_id).model_dump(mode="json"),
            )
            await _send_websocket_text(ws, json.dumps(msg.model_dump(mode="json")))

    async def get_decisions(self, limit: int = 50) -> List[SchedulerDecision]:
        async with self._lock:
            return list(self._decisions[-limit:])

    async def get_fairness_metric(self) -> float:
        nodes = await self.registry.list_nodes()
        counts = [n.total_completed for n in nodes]
        return calculate_fairness_cv(counts)

    # ---------------------------------------------------------
    # Core Dispatch Loop
    # ---------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        while self.is_running:
            try:
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

        elif msg.message_type == MessageType.TASK_PROGRESS:
            task_id = msg.payload.get("task_id")
            pct = float(msg.payload.get("progress", 0.0))
            if task_id:
                task = await self.repo.get(task_id)
                if task:
                    task.progress = pct
                    await self.repo.save(task)

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
        else:
            # Retries exhausted -> Move to Dead-Letter Queue (DLQ)
            logger.error(f"Task [{task_id}] permanently failed after retries. Moving to DLQ: {decision.reason}")
            await self.dlq.add(task, final_error=decision.reason)
            await self.repo.save(task)

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
