"""Binary protocol framing, chunking, and integrity verification."""

import hashlib
import hmac
import struct
from typing import List, Tuple

HEADER_MAGIC = b"TMCH"
HEADER_FORMAT = ">4s36sII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 + 36 + 4 + 4 = 48 bytes


def compute_payload_sha256(payload: bytes) -> str:
    """Computes SHA-256 hex digest of raw binary bytes."""
    return hashlib.sha256(payload).hexdigest()


def verify_payload_checksum(payload: bytes, expected_checksum: str) -> bool:
    """Constant-time verification of payload checksum."""
    if not expected_checksum:
        return False
    # Normalize if expected has 'sha256:' prefix
    clean_expected = expected_checksum.lower().replace("sha256:", "")
    actual = compute_payload_sha256(payload).lower()
    return hmac.compare_digest(actual, clean_expected)


def create_binary_chunk_frame(
    task_id: str,
    chunk_index: int,
    total_chunks: int,
    chunk_data: bytes,
) -> bytes:
    """Packs chunk into a binary frame with fixed 48-byte header."""
    # Ensure task_id fits in 36 bytes ascii
    tid_bytes = task_id.encode("utf-8")[:36].ljust(36, b" ")
    header = struct.pack(HEADER_FORMAT, HEADER_MAGIC, tid_bytes, chunk_index, total_chunks)
    return header + chunk_data


def parse_binary_chunk_frame(frame: bytes) -> Tuple[str, int, int, bytes]:
    """Unpacks binary chunk frame and validates header.
    
    Returns: (task_id, chunk_index, total_chunks, chunk_data)
    """
    if len(frame) < HEADER_SIZE:
        raise ValueError(f"Binary frame too short ({len(frame)} < {HEADER_SIZE} bytes)")

    magic, tid_bytes, chunk_index, total_chunks = struct.unpack_from(HEADER_FORMAT, frame, 0)
    if magic != HEADER_MAGIC:
        raise ValueError(f"Invalid binary frame magic: expected {HEADER_MAGIC}, got {magic}")

    task_id = tid_bytes.decode("utf-8").strip()
    chunk_data = frame[HEADER_SIZE:]
    return task_id, chunk_index, total_chunks, chunk_data


def split_into_chunks(payload_bytes: bytes, chunk_size: int = 65536) -> List[bytes]:
    """Splits payload bytes into chunks of specified maximum size."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not payload_bytes:
        return [b""]

    chunks = []
    total_len = len(payload_bytes)
    for i in range(0, total_len, chunk_size):
        chunks.append(payload_bytes[i : i + chunk_size])
    return chunks
