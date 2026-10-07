"""HMAC message integrity, authentication, and replay protection for TaskMesh."""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Dict, Optional, Set, Tuple

from taskmesh.protocol.messages import ProtocolMessage


def serialize_for_signature(msg: ProtocolMessage) -> bytes:
    """Produces a canonical deterministic byte string for HMAC signing."""
    components = [
        str(msg.protocol_version),
        str(msg.message_id),
        str(msg.message_type.value),
        str(msg.node_id or ""),
        msg.timestamp.isoformat(),
        str(msg.sequence_number or 0),
        json.dumps(msg.payload, sort_keys=True, separators=(",", ":")),
    ]
    return "|".join(components).encode("utf-8")


def compute_hmac_signature(msg: ProtocolMessage, secret: str) -> str:
    """Computes HMAC-SHA256 signature for a protocol message."""
    canonical_bytes = serialize_for_signature(msg)
    return hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()


def verify_hmac_signature(msg: ProtocolMessage, secret: str) -> bool:
    """Verifies that the message's signature matches the expected HMAC-SHA256."""
    if not msg.signature:
        return False
    expected = compute_hmac_signature(msg, secret)
    return hmac.compare_digest(msg.signature, expected)


class SecurityManager:
    """Manages node authentication, HMAC integrity verification, and replay protection."""

    def __init__(
        self,
        secret_key: str,
        secure_mode: bool = False,
        max_skew_seconds: float = 60.0,
    ) -> None:
        self.secret_key = secret_key
        self.secure_mode = secure_mode
        self.max_skew_seconds = max_skew_seconds
        self._seen_message_ids: Set[str] = set()
        self._last_sequence: Dict[str, int] = {}  # node_id -> last_seq

    def sign(self, msg: ProtocolMessage) -> ProtocolMessage:
        """Signs the message with the HMAC secret key."""
        msg.signature = compute_hmac_signature(msg, self.secret_key)
        return msg

    def validate_incoming(self, msg: ProtocolMessage) -> Tuple[bool, Optional[str]]:
        """Validates incoming message authenticity, integrity, and freshness.
        
        Returns (is_valid, error_reason).
        """
        # In insecure development mode, skip cryptographic validation
        if not self.secure_mode:
            return True, None

        # 1. HMAC Signature verification
        if not msg.signature:
            return False, "Missing HMAC signature in secure mode"

        if not verify_hmac_signature(msg, self.secret_key):
            return False, "Invalid HMAC signature or message payload tampered"

        # 2. Timestamp freshness check (prevent delayed replay attacks)
        now = datetime.now(timezone.utc)
        skew = abs((now - msg.timestamp).total_seconds())
        if skew > self.max_skew_seconds:
            return False, f"Message timestamp expired (skew: {skew:.1f}s > {self.max_skew_seconds}s)"

        # 3. Message ID uniqueness check (prevent duplicate replays)
        if msg.message_id in self._seen_message_ids:
            return False, f"Replay attack detected: duplicate message_id '{msg.message_id}'"
        self._seen_message_ids.add(msg.message_id)

        # 4. Sequence number monotonicity check per node
        if msg.node_id and msg.sequence_number is not None:
            last_seq = self._last_sequence.get(msg.node_id, -1)
            if msg.sequence_number <= last_seq:
                return False, f"Replay attack detected: non-monotonic sequence {msg.sequence_number} <= {last_seq}"
            self._last_sequence[msg.node_id] = msg.sequence_number

        return True, None
