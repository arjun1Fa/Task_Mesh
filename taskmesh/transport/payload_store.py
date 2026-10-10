"""In-memory safe payload store and chunk reassembly engine."""

import asyncio
import math
from typing import Dict, List, Optional, Tuple

from taskmesh.core.models import BinaryPayloadMeta
from taskmesh.transport.binary_protocol import (
    compute_payload_sha256,
    verify_payload_checksum,
)


class PayloadSizeLimitExceededError(ValueError):
    """Raised when payload exceeds safe size limits."""
    pass


class PayloadChecksumMismatchError(ValueError):
    """Raised when reassembled payload does not match expected SHA-256."""
    pass


class BinaryPayloadStore:
    """Thread-safe payload storage enforcing maximum size limits."""

    def __init__(self, max_payload_size_bytes: int = 50 * 1024 * 1024) -> None:
        self.max_payload_size_bytes = max_payload_size_bytes
        self._store: Dict[str, bytes] = {}
        self._meta: Dict[str, BinaryPayloadMeta] = {}
        self._lock = asyncio.Lock()

    async def add_payload(
        self,
        task_id: str,
        data: bytes,
        workload_type: str = "image_inference",
        model_identifier: str = "yolov8n",
        mime_type: str = "image/jpeg",
        chunk_size_bytes: int = 65536,
        stream_id: Optional[str] = None,
        frame_id: Optional[int] = None,
    ) -> BinaryPayloadMeta:
        """Stores binary payload after enforcing size limit and computing checksum."""
        if len(data) > self.max_payload_size_bytes:
            raise PayloadSizeLimitExceededError(
                f"Payload size {len(data)} bytes exceeds limit {self.max_payload_size_bytes} bytes"
            )

        checksum = compute_payload_sha256(data)
        total_chunks = max(1, math.ceil(len(data) / chunk_size_bytes)) if len(data) > 0 else 1

        meta = BinaryPayloadMeta(
            task_id=task_id,
            workload_type=workload_type,
            model_identifier=model_identifier,
            payload_size_bytes=len(data),
            mime_type=mime_type,
            checksum_sha256=checksum,
            chunk_size_bytes=chunk_size_bytes,
            total_chunks=total_chunks,
            stream_id=stream_id,
            frame_id=frame_id,
        )

        async with self._lock:
            self._store[task_id] = data
            self._meta[task_id] = meta

        return meta

    async def get_payload(self, task_id: str) -> Optional[bytes]:
        async with self._lock:
            return self._store.get(task_id)

    async def get_meta(self, task_id: str) -> Optional[BinaryPayloadMeta]:
        async with self._lock:
            return self._meta.get(task_id)

    async def remove_payload(self, task_id: str) -> None:
        async with self._lock:
            self._store.pop(task_id, None)
            self._meta.pop(task_id, None)


class ChunkAssembler:
    """Collects and reassembles incoming binary chunk frames."""

    def __init__(self, max_payload_size_bytes: int = 50 * 1024 * 1024) -> None:
        self.max_payload_size_bytes = max_payload_size_bytes
        # task_id -> {chunk_idx: chunk_data}
        self._buffers: Dict[str, Dict[int, bytes]] = {}
        self._buffered_sizes: Dict[str, int] = {}
        self._metas: Dict[str, BinaryPayloadMeta] = {}

    def register_expected_payload(self, meta: BinaryPayloadMeta) -> None:
        """Pre-registers expected payload metadata for validation."""
        self._metas[meta.task_id] = meta

    def add_chunk(
        self,
        task_id: str,
        chunk_index: int,
        total_chunks: int,
        chunk_data: bytes,
    ) -> Optional[bytes]:
        """Adds incoming chunk.
        
        Returns fully assembled bytes if all chunks received and verified,
        otherwise returns None.
        """
        current_size = self._buffered_sizes.get(task_id, 0) + len(chunk_data)
        if current_size > self.max_payload_size_bytes:
            self.discard(task_id)
            raise PayloadSizeLimitExceededError(
                f"Assembled size {current_size} exceeds limit {self.max_payload_size_bytes}"
            )

        if task_id not in self._buffers:
            self._buffers[task_id] = {}
            self._buffered_sizes[task_id] = 0

        self._buffers[task_id][chunk_index] = chunk_data
        self._buffered_sizes[task_id] += len(chunk_data)

        # Check if all chunks have arrived
        if len(self._buffers[task_id]) == total_chunks:
            # Reassemble in order
            ordered = [self._buffers[task_id][i] for i in range(total_chunks)]
            full_data = b"".join(ordered)

            # Check integrity if metadata registered
            meta = self._metas.pop(task_id, None)
            if meta and meta.checksum_sha256:
                if not verify_payload_checksum(full_data, meta.checksum_sha256):
                    self.discard(task_id)
                    raise PayloadChecksumMismatchError(
                        f"Checksum mismatch for task {task_id}: expected {meta.checksum_sha256}, got {compute_payload_sha256(full_data)}"
                    )

            # Clean buffer
            self.discard(task_id)
            return full_data

        return None

    def discard(self, task_id: str) -> None:
        """Cleans up buffer for task."""
        self._buffers.pop(task_id, None)
        self._buffered_sizes.pop(task_id, None)
        self._metas.pop(task_id, None)
