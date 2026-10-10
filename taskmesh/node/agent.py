"""Node Agent for distributed compute workers."""

import asyncio
import json
import logging
from typing import Optional
import websockets

from taskmesh.core.config import NodeConfig
from taskmesh.core.enums import MessageType, NodeStatus, TaskStatus
from taskmesh.core.models import BinaryPayloadMeta, CheckpointData, TaskResult, utc_now
from taskmesh.discovery.broadcast import NodeDiscoveryAdvertiser
from taskmesh.handlers.ai_inference import image_inference_handler
from taskmesh.handlers.builtin import cpu_test_handler, log_handler, sleep_handler
from taskmesh.node.hardware import collect_telemetry, profile_hardware
from taskmesh.node.worker_pool import WorkerPool
from taskmesh.security.hmac_auth import SecurityManager
from taskmesh.transport.binary_protocol import parse_binary_chunk_frame
from taskmesh.transport.payload_store import ChunkAssembler
from taskmesh.protocol.messages import (
    HeartbeatPayload,
    ProtocolMessage,
    RegisterAckPayload,
    RegisterNodePayload,
    TaskAcceptedPayload,
    TaskAssignmentPayload,
    TaskCheckpointPayload,
    TaskCompletedPayload,
    TaskFailedPayload,
    TaskProgressPayload,
    TaskRejectedPayload,
    TaskStartedPayload,
    TelemetryPayload,
)

logger = logging.getLogger("taskmesh.node")


class NodeAgent:
    """TaskMesh compute node agent communicating over WebSocket with Orchestrator."""

    def __init__(self, config: Optional[NodeConfig] = None) -> None:
        self.config = config or NodeConfig()
        self.node_id = self.config.node_id
        self.pool = WorkerPool(concurrency=self.config.worker_concurrency)
        self.status = NodeStatus.ONLINE
        self.is_running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._seq_num = 0
        self.security = SecurityManager(secret_key=self.config.join_token, secure_mode=self.config.secure_mode)

        # Binary chunk assembly and wireless state
        self.chunk_assembler = ChunkAssembler(max_payload_size_bytes=self.config.max_payload_size_bytes)
        self._binary_payloads: dict[str, bytes] = {}
        self._payload_events: dict[str, asyncio.Event] = {}
        self.rtt_ms_ewma: float = 0.0
        self.upload_mbps_ewma: float = 0.0
        self.download_mbps_ewma: float = 0.0
        self.advertiser: Optional[NodeDiscoveryAdvertiser] = None

        # Register default handlers
        self.pool.register_handler("log", log_handler)
        self.pool.register_handler("sleep", sleep_handler)
        self.pool.register_handler("cpu_test", cpu_test_handler)
        self.pool.register_handler("image_inference", image_inference_handler)

        tags = [t.strip() for t in self.config.tags.split(",") if t.strip()]
        self.capabilities = profile_hardware(
            supported_handlers=self.pool.get_supported_handlers(),
            tags=tags,
            ip_address=self.config.lan_ip,
            is_local=self.config.is_local,
            port=self.config.lan_port or 8000,
        )


    async def start(self) -> None:
        self.is_running = True
        if self.config.enable_discovery:
            self.advertiser = NodeDiscoveryAdvertiser(
                node_id=self.node_id,
                capabilities=self.capabilities,
                port=self.config.discovery_port,
                ws_port=self.config.lan_port or 8000,
                orchestrator_url=self.config.orchestrator_url,
                lan_ip=self.config.lan_ip,
            )
            await self.advertiser.start()

        urls = [self.config.orchestrator_url]
        if self.config.standby_url and self.config.standby_url not in urls:
            urls.append(self.config.standby_url)
        url_idx = 0
        logger.info(f"Starting TaskMesh Node Agent [{self.node_id}] targeting {urls}")

        while self.is_running:
            target_url = urls[url_idx % len(urls)]
            try:
                async with websockets.connect(target_url) as ws:
                    self._ws = ws
                    logger.info(f"Connected to orchestrator at {target_url}")

                    # 1. Register with orchestrator
                    registered = await self._register()
                    if not registered:
                        logger.error("Node registration rejected, retrying in 2s...")
                        url_idx += 1
                        await asyncio.sleep(2.0)
                        continue

                    # 2. Run concurrent heartbeat, telemetry, and message receiver loops
                    hb_task = asyncio.create_task(self._heartbeat_loop())
                    telem_task = asyncio.create_task(self._telemetry_loop())
                    msg_task = asyncio.create_task(self._listen_loop())

                    done, pending = await asyncio.wait(
                        [hb_task, telem_task, msg_task],
                        return_when=asyncio.FIRST_EXCEPTION
                    )
                    for task in pending:
                        task.cancel()

            except (websockets.ConnectionClosed, OSError) as e:
                logger.warning(f"Connection to {target_url} lost ({e}), attempting reconnection...")
                self._ws = None
                url_idx += 1
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Unexpected error in agent loop targeting {target_url}: {e}", exc_info=True)
                url_idx += 1
                await asyncio.sleep(1.0)

    async def stop(self) -> None:
        self.is_running = False
        self.status = NodeStatus.OFFLINE
        if self.advertiser:
            await self.advertiser.stop()
        if self._ws:
            await self._ws.close()
        await self.pool.shutdown()
        logger.info(f"Node Agent [{self.node_id}] stopped cleanly")

    async def _send(self, msg_type: MessageType, payload_dict: dict) -> None:
        if not self._ws:
            return
        self._seq_num += 1
        envelope = ProtocolMessage(
            message_type=msg_type,
            node_id=self.node_id,
            sequence_number=self._seq_num,
            payload=payload_dict,
        )
        self.security.sign(envelope)
        data = json.dumps(envelope.model_dump(mode="json"))
        await self._ws.send(data)

    async def _register(self) -> bool:
        reg_payload = RegisterNodePayload(
            node_id=self.node_id,
            token=self.config.join_token,
            capabilities=self.capabilities,
        )
        await self._send(MessageType.REGISTER_NODE, reg_payload.model_dump(mode="json"))

        # Await RegisterAck response
        raw_resp = await self._ws.recv()
        msg = ProtocolMessage.model_validate(json.loads(raw_resp))
        if msg.message_type == MessageType.REGISTER_ACK:
            ack = RegisterAckPayload.model_validate(msg.payload)
            if ack.accepted:
                logger.info(f"Node successfully registered: {ack.message}")
                return True
        return False

    async def _heartbeat_loop(self) -> None:
        while self.is_running and self._ws:
            hb = HeartbeatPayload(
                node_id=self.node_id,
                sequence_number=self._seq_num,
                status=self.status,
                active_tasks=self.pool.active_count,
            )
            await self._send(MessageType.HEARTBEAT, hb.model_dump(mode="json"))
            # Send periodic ping to track network RTT
            if self._seq_num % 3 == 0:
                await self._send(MessageType.PING, {})
            await asyncio.sleep(self.config.heartbeat_interval_seconds)

    async def _telemetry_loop(self) -> None:
        while self.is_running and self._ws:
            telem = collect_telemetry(
                node_id=self.node_id,
                active_tasks=self.pool.active_count,
                queued_tasks=0,
                rtt_ms_ewma=self.rtt_ms_ewma,
                upload_mbps_ewma=self.upload_mbps_ewma,
                download_mbps_ewma=self.download_mbps_ewma,
            )
            msg = TelemetryPayload(node_id=self.node_id, telemetry=telem)
            await self._send(MessageType.TELEMETRY, msg.model_dump(mode="json"))
            await asyncio.sleep(self.config.telemetry_interval_seconds)

    async def _listen_loop(self) -> None:
        async for raw_msg in self._ws:
            try:
                # Handle binary frames (chunks)
                if isinstance(raw_msg, bytes):
                    try:
                        task_id, chunk_idx, total_chunks, chunk_data = parse_binary_chunk_frame(raw_msg)
                        assembled = self.chunk_assembler.add_chunk(task_id, chunk_idx, total_chunks, chunk_data)
                        if assembled is not None:
                            self._binary_payloads[task_id] = assembled
                            if task_id in self._payload_events:
                                self._payload_events[task_id].set()
                    except Exception as e:
                        logger.error(f"Error assembling binary chunk: {e}", exc_info=True)
                    continue

                # Handle JSON text frames
                data = json.loads(raw_msg)
                msg = ProtocolMessage.model_validate(data)
                is_valid, sec_err = self.security.validate_incoming(msg)
                if not is_valid:
                    logger.warning(f"Rejected message from orchestrator: {sec_err}")
                    continue
                await self._handle_message(msg)
            except Exception as e:
                logger.error(f"Error handling incoming message: {e}", exc_info=True)

    async def _handle_message(self, msg: ProtocolMessage) -> None:
        if msg.message_type == MessageType.TASK_ASSIGNMENT:
            assignment = TaskAssignmentPayload.model_validate(msg.payload)
            asyncio.create_task(self._process_assignment(assignment))

        elif msg.message_type == MessageType.TASK_CANCEL:
            task_id = msg.payload.get("task_id")
            if task_id:
                logger.info(f"Received cancel request for task {task_id}")
                await self.pool.cancel_task(task_id)

        elif msg.message_type == MessageType.NODE_DRAIN:
            logger.info(f"Node [{self.node_id}] instructed to DRAIN")
            self.status = NodeStatus.DRAINING

        elif msg.message_type == MessageType.PONG:
            orig_str = msg.payload.get("orig_timestamp")
            if orig_str:
                try:
                    orig = datetime.fromisoformat(orig_str)
                    rtt = (utc_now() - orig).total_seconds() * 1000.0
                    if rtt > 0:
                        self.rtt_ms_ewma = (0.75 * self.rtt_ms_ewma + 0.25 * rtt) if self.rtt_ms_ewma > 0 else rtt
                except Exception:
                    pass

    async def _process_assignment(self, assignment: TaskAssignmentPayload) -> None:
        task_id = assignment.task_id
        attempt_id = assignment.attempt_id

        if self.status == NodeStatus.DRAINING:
            rej = TaskRejectedPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id, reason="Node draining")
            await self._send(MessageType.TASK_REJECTED, rej.model_dump(mode="json"))
            return

        # 1. Send Task Accepted
        acc = TaskAcceptedPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id)
        await self._send(MessageType.TASK_ACCEPTED, acc.model_dump(mode="json"))

        # 2. Send Task Started
        started = TaskStartedPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id)
        await self._send(MessageType.TASK_STARTED, started.model_dump(mode="json"))

        # 3. Handle binary payload if expected
        binary_bytes = None
        if assignment.payload.get("has_binary_payload"):
            meta_dict = assignment.payload.get("binary_meta")
            if meta_dict:
                meta = BinaryPayloadMeta.model_validate(meta_dict)
                self.chunk_assembler.register_expected_payload(meta)

            if task_id not in self._binary_payloads:
                ev = asyncio.Event()
                self._payload_events[task_id] = ev
                try:
                    await asyncio.wait_for(ev.wait(), timeout=min(25.0, assignment.timeout_seconds))
                except asyncio.TimeoutError:
                    fail_payload = TaskFailedPayload(
                        task_id=task_id,
                        attempt_id=attempt_id,
                        node_id=self.node_id,
                        error="Timed out waiting for binary payload chunks",
                    )
                    await self._send(MessageType.TASK_FAILED, fail_payload.model_dump(mode="json"))
                    return
                finally:
                    self._payload_events.pop(task_id, None)

            binary_bytes = self._binary_payloads.pop(task_id, None)

        # Progress and checkpoint callbacks
        async def on_progress(pct: float, message: str) -> None:
            p_payload = TaskProgressPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id, progress=pct, message=message)
            await self._send(MessageType.TASK_PROGRESS, p_payload.model_dump(mode="json"))

        async def on_checkpoint(cp_data: CheckpointData) -> None:
            c_payload = TaskCheckpointPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id, checkpoint=cp_data)
            await self._send(MessageType.TASK_CHECKPOINT, c_payload.model_dump(mode="json"))

        # 4. Execute work
        result: TaskResult = await self.pool.execute_assignment(
            assignment=assignment,
            node_id=self.node_id,
            progress_callback=on_progress,
            checkpoint_callback=on_checkpoint,
            binary_payload=binary_bytes,
        )

        # 5. Return result
        if result.status == TaskStatus.COMPLETED:
            done_payload = TaskCompletedPayload(task_id=task_id, attempt_id=attempt_id, node_id=self.node_id, result=result)
            await self._send(MessageType.TASK_COMPLETED, done_payload.model_dump(mode="json"))
        else:
            fail_payload = TaskFailedPayload(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=self.node_id,
                error=result.error or "Unknown execution failure",
                execution_time_seconds=result.execution_time_seconds,
            )
            await self._send(MessageType.TASK_FAILED, fail_payload.model_dump(mode="json"))

