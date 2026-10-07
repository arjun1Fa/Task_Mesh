"""Unit tests for HMAC security, integrity verification, and replay protection."""

from datetime import datetime, timedelta, timezone
import pytest

from taskmesh.core.enums import MessageType
from taskmesh.protocol.messages import HeartbeatPayload, ProtocolMessage
from taskmesh.security.hmac_auth import SecurityManager, compute_hmac_signature


def test_valid_signed_message_accepted():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=1,
        payload=HeartbeatPayload(node_id="node-1", sequence_number=1).model_dump(mode="json"),
    )
    sec.sign(msg)
    valid, err = sec.validate_incoming(msg)
    assert valid is True
    assert err is None


def test_invalid_hmac_rejected():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=1,
        payload={"data": "test"},
    )
    sec.sign(msg)
    # Corrupt signature
    msg.signature = "bad-signature-12345"

    valid, err = sec.validate_incoming(msg)
    assert valid is False
    assert "Invalid HMAC signature" in err


def test_modified_payload_rejected():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=1,
        payload={"value": 100},
    )
    sec.sign(msg)

    # Tamper with payload after signing
    msg.payload["value"] = 999

    valid, err = sec.validate_incoming(msg)
    assert valid is False
    assert "Invalid HMAC signature or message payload tampered" in err


def test_replayed_message_id_rejected():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=1,
        payload={"test": 1},
    )
    sec.sign(msg)

    # First validation succeeds
    valid1, _ = sec.validate_incoming(msg)
    assert valid1 is True

    # Replay of exact same message fails
    valid2, err = sec.validate_incoming(msg)
    assert valid2 is False
    assert "Replay attack detected: duplicate message_id" in err


def test_stale_sequence_number_rejected():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True)
    msg1 = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=5,
        payload={},
    )
    sec.sign(msg1)
    valid1, _ = sec.validate_incoming(msg1)
    assert valid1 is True

    # Out-of-order / replay sequence number 4 <= 5
    msg2 = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        sequence_number=4,
        payload={},
    )
    sec.sign(msg2)
    valid2, err = sec.validate_incoming(msg2)
    assert valid2 is False
    assert "Replay attack detected: non-monotonic sequence" in err


def test_expired_timestamp_rejected():
    sec = SecurityManager(secret_key="my-cluster-secret", secure_mode=True, max_skew_seconds=30.0)
    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        timestamp=old_time,
        sequence_number=1,
        payload={},
    )
    sec.sign(msg)

    valid, err = sec.validate_incoming(msg)
    assert valid is False
    assert "Message timestamp expired" in err


def test_insecure_mode_allows_unsigned():
    sec = SecurityManager(secret_key="secret", secure_mode=False)
    msg = ProtocolMessage(
        message_type=MessageType.HEARTBEAT,
        node_id="node-1",
        payload={},
    )
    valid, err = sec.validate_incoming(msg)
    assert valid is True
    assert err is None
