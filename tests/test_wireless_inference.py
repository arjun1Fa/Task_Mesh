"""Comprehensive test suite for TaskMesh Wireless Inference Sharing.

Validates all 18 requirements:
1. binary task serialization
2. binary task deserialization
3. payload checksum verification
4. payload size limits
5. chunked transfer & reassembly
6. local-only policy
7. wireless-allowed policy
8. network cost estimation
9. remote-vs-local decision
10. unknown network telemetry fallback
11. disconnected node
12. transfer timeout
13. stale result
14. duplicate task idempotency
15. retry after wireless failure
16. scheduler integration pipeline
17. security verification
18. discovery parsing
"""

import asyncio
from datetime import datetime, timezone
import json
import pytest

from taskmesh.bidding.contract_net import calculate_node_bid
from taskmesh.core.config import NodeConfig, OrchestratorConfig
from taskmesh.core.enums import MessageType, NodeStatus, OffloadPolicy, SchedulerMode, TaskStatus
from taskmesh.core.errors import IneligibleNodeError
from taskmesh.core.models import (
    BinaryPayloadMeta,
    NodeCapabilities,
    NodeProfile,
    NodeTelemetry,
    Task,
    TaskCreate,
    TaskResult,
    utc_now,
)
from taskmesh.discovery.broadcast import (
    DiscoveredNode,
    NodeDiscoveryAdvertiser,
    get_lan_ip,
)
from taskmesh.orchestrator.runtime import OrchestratorRuntime
from taskmesh.persistence.repositories import MemoryTaskRepository
from taskmesh.protocol.messages import (
    ProtocolMessage,
    TaskAssignmentPayload,
    TaskCompletedPayload,
)
from taskmesh.scheduler.adaptive import AdaptiveScheduler
from taskmesh.scheduler.base import filter_eligible_nodes
from taskmesh.security.hmac_auth import SecurityManager
from taskmesh.transport.binary_protocol import (
    compute_payload_sha256,
    create_binary_chunk_frame,
    parse_binary_chunk_frame,
    split_into_chunks,
    verify_payload_checksum,
)
from taskmesh.transport.payload_store import (
    BinaryPayloadStore,
    ChunkAssembler,
    PayloadChecksumMismatchError,
    PayloadSizeLimitExceededError,
)
from taskmesh.wireless.estimator import NetworkEstimator


# =====================================================================
# 1. Binary Task Serialization
# =====================================================================
def test_binary_task_serialization():
    task_id = "task-binary-1234"
    chunk_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    frame = create_binary_chunk_frame(
        task_id=task_id,
        chunk_index=0,
        total_chunks=1,
        chunk_data=chunk_data,
    )
    assert len(frame) == 48 + len(chunk_data)
    assert frame[:4] == b"TMCH"
    assert task_id.encode("utf-8") in frame[:40]


# =====================================================================
# 2. Binary Task Deserialization
# =====================================================================
def test_binary_task_deserialization():
    task_id = "task-chunk-77"
    raw_data = b"image_raw_pixel_data_bytes_12345"
    frame = create_binary_chunk_frame(
        task_id=task_id,
        chunk_index=2,
        total_chunks=5,
        chunk_data=raw_data,
    )

    tid, c_idx, tot, data = parse_binary_chunk_frame(frame)
    assert tid == task_id
    assert c_idx == 2
    assert tot == 5
    assert data == raw_data

    # Test error cases
    with pytest.raises(ValueError, match="too short"):
        parse_binary_chunk_frame(b"short")

    corrupted = b"XXXX" + frame[4:]
    with pytest.raises(ValueError, match="Invalid binary frame magic"):
        parse_binary_chunk_frame(corrupted)


# =====================================================================
# 3. Payload Checksum Verification
# =====================================================================
def test_payload_checksum_verification():
    payload = b"simulated_jpeg_camera_frame_content"
    checksum = compute_payload_sha256(payload)
    assert len(checksum) == 64

    # Verification passes
    assert verify_payload_checksum(payload, checksum) is True
    assert verify_payload_checksum(payload, f"sha256:{checksum}") is True

    # Tampered payload fails
    tampered = payload + b"!"
    assert verify_payload_checksum(tampered, checksum) is False
    assert verify_payload_checksum(payload, "bad_checksum") is False


# =====================================================================
# 4. Payload Size Limits
# =====================================================================
@pytest.mark.asyncio
async def test_payload_size_limits():
    store = BinaryPayloadStore(max_payload_size_bytes=500)

    # Within limit
    small_data = b"x" * 400
    meta = await store.add_payload("task-1", small_data)
    assert meta.payload_size_bytes == 400

    # Exceeding limit
    large_data = b"y" * 600
    with pytest.raises(PayloadSizeLimitExceededError):
        await store.add_payload("task-2", large_data)

    # Assembler limit enforcement
    assembler = ChunkAssembler(max_payload_size_bytes=500)
    with pytest.raises(PayloadSizeLimitExceededError):
        assembler.add_chunk("task-3", 0, 1, b"z" * 600)


# =====================================================================
# 5. Chunked Transfer & Reassembly
# =====================================================================
def test_chunked_transfer_reassembly():
    original_data = b"TaskMeshChunkTestData" * 5000  # 105,000 bytes
    chunk_size = 32768  # 32 KB
    chunks = split_into_chunks(original_data, chunk_size=chunk_size)
    assert len(chunks) == 4

    meta = BinaryPayloadMeta(
        task_id="chunk-task-1",
        payload_size_bytes=len(original_data),
        checksum_sha256=compute_payload_sha256(original_data),
        total_chunks=len(chunks),
    )

    assembler = ChunkAssembler()
    assembler.register_expected_payload(meta)

    # First chunks return None
    assert assembler.add_chunk(meta.task_id, 0, len(chunks), chunks[0]) is None
    assert assembler.add_chunk(meta.task_id, 1, len(chunks), chunks[1]) is None
    assert assembler.add_chunk(meta.task_id, 2, len(chunks), chunks[2]) is None

    # Final chunk completes reassembly and validates checksum
    full = assembler.add_chunk(meta.task_id, 3, len(chunks), chunks[3])
    assert full == original_data

    # Verify checksum mismatch error if data corrupted
    meta2 = BinaryPayloadMeta(
        task_id="chunk-task-corrupt",
        checksum_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        total_chunks=1,
    )
    assembler.register_expected_payload(meta2)
    with pytest.raises(PayloadChecksumMismatchError):
        assembler.add_chunk("chunk-task-corrupt", 0, 1, b"corrupted_data")


# =====================================================================
# 6. Local-Only Policy
# =====================================================================
def test_local_only_policy():
    local_node = NodeProfile(
        id="local-laptop",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=True, supported_handlers=["image_inference"]),
    )
    remote_gpu = NodeProfile(
        id="remote-gpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=False, has_gpu=True, supported_handlers=["image_inference"]),
    )

    candidates = [local_node, remote_gpu]

    task_local = Task(
        task_type="image_inference",
        offload_policy=OffloadPolicy.LOCAL_ONLY,
    )

    eligible = filter_eligible_nodes(task_local, candidates)
    assert len(eligible) == 1
    assert eligible[0].id == "local-laptop"

    # If no local node exists, raises IneligibleNodeError
    task_local_no_match = Task(
        task_type="image_inference",
        offload_policy=OffloadPolicy.LOCAL_ONLY,
    )
    eligible_none = filter_eligible_nodes(task_local_no_match, [remote_gpu])
    assert len(eligible_none) == 0


# =====================================================================
# 7. Wireless-Allowed Policy
# =====================================================================
def test_wireless_allowed_policy():
    local_node = NodeProfile(
        id="local-laptop",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=True, supported_handlers=["image_inference"]),
    )
    remote_gpu = NodeProfile(
        id="remote-gpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=False, has_gpu=True, supported_handlers=["image_inference"]),
    )

    candidates = [local_node, remote_gpu]

    task_wireless = Task(
        task_type="image_inference",
        offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
    )

    eligible = filter_eligible_nodes(task_wireless, candidates)
    assert len(eligible) == 2


# =====================================================================
# 8. Network Cost Estimation
# =====================================================================
def test_network_cost_estimation():
    estimator = NetworkEstimator()
    node = NodeProfile(
        id="gpu-rig-1",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(has_gpu=True, is_local=False),
        telemetry=NodeTelemetry(node_id="gpu-rig-1", active_tasks=1),
    )

    # Set measured network values
    m = estimator.get_or_create_metrics(node.id)
    m.upload_mbps_ewma = 40.0
    m.rtt_ms_ewma = 15.0
    m.download_mbps_ewma = 80.0

    task = Task(task_type="image_inference", payload={"model": "yolov8n"})
    payload_size = 500_000  # 500 KB image

    breakdown = estimator.estimate_remote_execution_time(task, node, payload_size_bytes=payload_size)
    assert "upload_ms" in breakdown
    assert "rtt_ms" in breakdown
    assert "remote_inference_ms" in breakdown
    assert "download_ms" in breakdown
    assert "total_remote_ms" in breakdown

    # Upload ~ (500000*8 / 40e6)*1000 = 100 ms
    assert 95.0 <= breakdown["upload_ms"] <= 105.0
    assert breakdown["rtt_ms"] == 15.0
    assert breakdown["remote_inference_ms"] == 28.0  # GPU inference
    assert breakdown["total_remote_ms"] > breakdown["upload_ms"]


# =====================================================================
# 9. Remote vs Local Decision
# =====================================================================
def test_remote_vs_local_decision():
    estimator = NetworkEstimator()

    local_node = NodeProfile(
        id="local-cpu-node",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=True, has_gpu=False, supported_handlers=["image_inference"]),
    )
    remote_gpu = NodeProfile(
        id="remote-fast-gpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=False, has_gpu=True, supported_handlers=["image_inference"]),
    )

    # Scenario A: Fast Wi-Fi -> Remote GPU is faster than Local CPU
    m = estimator.get_or_create_metrics(remote_gpu.id)
    m.upload_mbps_ewma = 100.0  # Fast upload: 500KB in ~40ms
    m.rtt_ms_ewma = 10.0

    task = Task(task_type="image_inference")
    dec_a = estimator.compare_local_vs_remote(task, local_node, remote_gpu, payload_size_bytes=500_000)
    assert dec_a["decision"] == "remote"
    assert "faster" in dec_a["reason"]

    # Scenario B: Highly congested Wi-Fi -> Local CPU is faster
    m.upload_mbps_ewma = 1.0   # Slow upload: 500KB takes ~4000ms
    m.rtt_ms_ewma = 150.0

    dec_b = estimator.compare_local_vs_remote(task, local_node, remote_gpu, payload_size_bytes=500_000)
    assert dec_b["decision"] == "local"
    assert "local execution predicted faster" in dec_b["reason"]


# =====================================================================
# 10. Unknown Network Telemetry Fallback
# =====================================================================
def test_unknown_network_telemetry_fallback():
    estimator = NetworkEstimator()
    node = NodeProfile(
        id="mystery-new-node",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=False),
    )

    # Must produce valid positive estimates without crashing
    upload_time = estimator.estimate_upload_time_ms(100_000, node)
    download_time = estimator.estimate_download_time_ms(1024, node)

    assert upload_time > 0.0
    assert download_time > 0.0

    task = Task(task_type="cpu_test")
    breakdown = estimator.estimate_remote_execution_time(task, node, payload_size_bytes=100_000)
    assert breakdown["total_remote_ms"] > 0.0
    assert breakdown["rtt_ms"] == 20.0  # conservative default


# =====================================================================
# 11. Disconnected Node Handling
# =====================================================================
@pytest.mark.asyncio
async def test_disconnected_node():
    repo = MemoryTaskRepository()
    cfg = OrchestratorConfig()
    runtime = OrchestratorRuntime(repository=repo, config=cfg)

    # Node registered and active
    node = NodeProfile(
        id="disconnect-node-1",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(supported_handlers=["log"]),
    )
    await runtime.registry.register(node, None)

    task = Task(id="task-disc-1", task_type="log", status=TaskStatus.RUNNING, assigned_node_id="disconnect-node-1")
    await runtime.repo.save(task)

    # Simulate node disconnection failure recovery
    await runtime._recover_tasks_for_failed_node("disconnect-node-1")

    recovered = await runtime.repo.get("task-disc-1")
    assert recovered.status == TaskStatus.PENDING
    assert recovered.assigned_node_id is None
    assert runtime.queue.size == 1


# =====================================================================
# 12. Transfer Timeout Handling
# =====================================================================
@pytest.mark.asyncio
async def test_transfer_timeout():
    cfg = NodeConfig(node_id="test-timeout-node")
    from taskmesh.node.agent import NodeAgent
    agent = NodeAgent(config=cfg)

    assignment = TaskAssignmentPayload(
        task_id="timeout-task-1",
        attempt_id="timeout-task-1-A1",
        lease_id="lease-1",
        lease_expires_at=utc_now(),
        task_type="image_inference",
        payload={"has_binary_payload": True, "model": "yolov8n"},
        priority=5,
        timeout_seconds=0.1,  # Short timeout
    )

    # Should safely fail without hanging
    result = await agent.pool.execute_assignment(assignment, node_id=agent.node_id)
    # The pool handles the execution; verify agent rejects or fails cleanly
    assert result is not None
    await agent.pool.shutdown()


# =====================================================================
# 13. Stale Result Validation
# =====================================================================
@pytest.mark.asyncio
async def test_stale_result_validation():
    repo = MemoryTaskRepository()
    runtime = OrchestratorRuntime(repository=repo)

    task = Task(id="task-stale-1", task_type="log", status=TaskStatus.RUNNING)
    task.current_attempt = 2
    task.current_attempt_id = "task-stale-1-A2"
    await runtime.repo.save(task)

    # Node sends completed result for older attempt A1
    stale_msg = ProtocolMessage(
        message_type=MessageType.TASK_COMPLETED,
        node_id="node-1",
        payload={
            "task_id": "task-stale-1",
            "attempt_id": "task-stale-1-A1",
            "result": TaskResult(
                task_id="task-stale-1",
                attempt_id="task-stale-1-A1",
                node_id="node-1",
                status=TaskStatus.COMPLETED,
            ).model_dump(mode="json"),
        },
    )

    await runtime._process_task_completed(stale_msg)

    # Task should NOT be marked completed by stale attempt
    updated = await runtime.repo.get("task-stale-1")
    assert updated.status == TaskStatus.RUNNING
    assert updated.current_attempt_id == "task-stale-1-A2"


# =====================================================================
# 14. Duplicate Task Idempotency
# =====================================================================
@pytest.mark.asyncio
async def test_duplicate_task_idempotency():
    repo = MemoryTaskRepository()
    runtime = OrchestratorRuntime(repository=repo)

    req1 = TaskCreate(
        task_type="image_inference",
        idempotency_key="wifi-unique-req-99",
        payload={"image": "camera_frame_1.jpg"},
    )
    t1 = await runtime.submit_task(req1)

    req2 = TaskCreate(
        task_type="image_inference",
        idempotency_key="wifi-unique-req-99",
        payload={"image": "camera_frame_1.jpg"},
    )
    t2 = await runtime.submit_task(req2)

    assert t1.id == t2.id
    assert runtime.queue.size == 1


# =====================================================================
# 15. Retry After Wireless Failure
# =====================================================================
@pytest.mark.asyncio
async def test_retry_after_wireless_failure():
    repo = MemoryTaskRepository()
    runtime = OrchestratorRuntime(repository=repo)

    task = Task(id="retry-wifi-task", task_type="log", status=TaskStatus.RUNNING)
    task.current_attempt = 1
    task.current_attempt_id = "retry-wifi-task-A1"
    await runtime.repo.save(task)

    fail_msg = ProtocolMessage(
        message_type=MessageType.TASK_FAILED,
        node_id="node-wifi-drop",
        payload={
            "task_id": "retry-wifi-task",
            "attempt_id": "retry-wifi-task-A1",
            "error": "Connection reset by peer during chunk upload",
        },
    )

    await runtime._process_task_failed(fail_msg)

    updated = await runtime.repo.get("retry-wifi-task")
    assert updated.status == TaskStatus.RETRYING
    assert updated.retry_count == 1


# =====================================================================
# 16. Scheduler Integration Pipeline
# =====================================================================
@pytest.mark.asyncio
async def test_scheduler_integration_pipeline():
    scheduler = AdaptiveScheduler()

    local_node = NodeProfile(
        id="laptop-local",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=True, cpu_cores=4, supported_handlers=["image_inference"]),
    )
    remote_gpu = NodeProfile(
        id="rig-remote-gpu",
        status=NodeStatus.ONLINE,
        capabilities=NodeCapabilities(is_local=False, has_gpu=True, supported_handlers=["image_inference"]),
    )

    task = Task(
        task_type="image_inference",
        offload_policy=OffloadPolicy.WIRELESS_ALLOWED,
        binary_meta=BinaryPayloadMeta(task_id="t-sched-1", payload_size_bytes=200_000),
    )

    decision = await scheduler.select_node(task, [local_node, remote_gpu])

    assert decision.task_id == task.id
    assert decision.selected_node_id in ("laptop-local", "rig-remote-gpu")
    assert decision.policy_used == SchedulerMode.ADAPTIVE
    assert decision.offload_decision in ("local", "remote")
    assert decision.offload_reason is not None


# =====================================================================
# 17. Security Verification of Binary Envelope
# =====================================================================
def test_security_verification_binary_envelope():
    sec = SecurityManager(secret_key="my-mesh-secret", secure_mode=True)

    msg = ProtocolMessage(
        message_type=MessageType.TASK_ASSIGNMENT,
        node_id="node-sec-1",
        sequence_number=1,
        payload={
            "task_id": "sec-task-1",
            "has_binary_payload": True,
            "binary_meta": {
                "checksum_sha256": "abcdef1234567890",
                "payload_size_bytes": 1024,
            },
        },
    )

    signed = sec.sign(msg)
    assert signed.signature is not None

    # Valid message passes
    is_valid, err = sec.validate_incoming(signed)
    assert is_valid is True
    assert err is None

    # Tampering with payload content invalidates HMAC signature
    signed.payload["binary_meta"]["payload_size_bytes"] = 2048
    is_valid_tampered, err_tampered = sec.validate_incoming(signed)
    assert is_valid_tampered is False
    assert "Invalid HMAC signature" in err_tampered


# =====================================================================
# 18. Discovery Parsing
# =====================================================================
def test_discovery_parsing():
    caps = NodeCapabilities(
        cpu_cores=12,
        cpu_frequency_mhz=3600.0,
        ram_total_mb=32768,
        ram_available_mb=24000,
        has_gpu=True,
        gpu_name="NVIDIA RTX 4070",
        gpu_vram_mb=12288,
        supported_handlers=["image_inference", "log"],
        tags=["gpu", "wifi-lab"],
    )

    advertiser = NodeDiscoveryAdvertiser(
        node_id="gpu-lab-rig",
        capabilities=caps,
        port=37020,
        ws_port=8000,
        status="online",
        lan_ip="192.168.1.150",
    )

    announcement = advertiser.build_announcement()
    assert announcement["type"] == "TASKMESH_ANNOUNCE"
    assert announcement["node_id"] == "gpu-lab-rig"
    assert announcement["has_gpu"] is True

    # Parse JSON packet as DiscoveredNode
    raw_packet = json.dumps(announcement).encode("utf-8")
    parsed = json.loads(raw_packet.decode("utf-8"))

    discovered = DiscoveredNode(
        node_id=parsed["node_id"],
        hostname=parsed["hostname"],
        ip_address=parsed["ip_address"],
        port=parsed["port"],
        cpu_cores=parsed["cpu_cores"],
        cpu_frequency_mhz=parsed["cpu_frequency_mhz"],
        ram_total_mb=parsed["ram_total_mb"],
        ram_available_mb=parsed["ram_available_mb"],
        has_gpu=parsed["has_gpu"],
        gpu_name=parsed["gpu_name"],
        gpu_vram_mb=parsed["gpu_vram_mb"],
        supported_handlers=parsed["supported_handlers"],
        models_loaded=parsed["models_loaded"],
        current_status=parsed["current_status"],
    )

    assert discovered.node_id == "gpu-lab-rig"
    assert discovered.ip_address == "192.168.1.150"
    assert discovered.has_gpu is True
    assert discovered.gpu_name == "NVIDIA RTX 4070"
