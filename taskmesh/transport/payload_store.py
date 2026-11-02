"""In-memory and persistent safe payload store and chunk reassembly engine."""

import asyncio
import math
import os
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
    """Thread-safe payload and artifact storage with persistent disk backup."""

    def __init__(
        self,
        max_payload_size_bytes: int = 50 * 1024 * 1024,
        storage_dir: Optional[str] = None,
    ) -> None:
        self.max_payload_size_bytes = max_payload_size_bytes
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), ".taskmesh", "artifacts")
        os.makedirs(self.storage_dir, exist_ok=True)
        self._store: Dict[str, bytes] = {}
        self._meta: Dict[str, BinaryPayloadMeta] = {}
        self._lock = asyncio.Lock()
        self._load_disk_artifacts()

    def _load_disk_artifacts(self) -> None:
        """Indexes pre-existing artifacts from disk storage."""
        if not os.path.exists(self.storage_dir):
            return
        try:
            for fname in os.listdir(self.storage_dir):
                if fname.endswith(".bin"):
                    key = fname[:-4]
                    fpath = os.path.join(self.storage_dir, fname)
                    try:
                        with open(fpath, "rb") as f:
                            self._store[key] = f.read()
                    except Exception:
                        pass
        except Exception:
            pass

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
        artifact_in_id = f"art_in_{task_id}"

        meta = BinaryPayloadMeta(
            payload_id=artifact_in_id,
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
            self._store[artifact_in_id] = data
            self._meta[task_id] = meta
            self._meta[artifact_in_id] = meta

        # Persist to disk for restart durability
        self._write_disk(task_id, data)
        self._write_disk(artifact_in_id, data)

        return meta

    async def add_artifact(
        self,
        artifact_id: str,
        data: bytes,
        mime_type: str = "image/jpeg",
        task_id: Optional[str] = None,
    ) -> str:
        """Stores a named artifact (e.g. annotated output image) with disk durability."""
        if len(data) > self.max_payload_size_bytes:
            raise PayloadSizeLimitExceededError(f"Artifact size {len(data)} exceeds limit")

        async with self._lock:
            self._store[artifact_id] = data
            if task_id:
                self._store[f"annotated_{task_id}"] = data
                self._store[f"art_out_{task_id}"] = data

        self._write_disk(artifact_id, data)
        if task_id:
            self._write_disk(f"annotated_{task_id}", data)
            self._write_disk(f"art_out_{task_id}", data)

        return artifact_id

    def _write_disk(self, key: str, data: bytes) -> None:
        try:
            safe_name = "".join(c for c in key if c.isalnum() or c in ("-", "_")) + ".bin"
            target = os.path.join(self.storage_dir, safe_name)
            with open(target, "wb") as f:
                f.write(data)
        except Exception:
            pass

    async def get_payload(self, task_id: str) -> Optional[bytes]:
        async with self._lock:
            if task_id in self._store:
                return self._store[task_id]
            art_id = f"art_in_{task_id}"
            if art_id in self._store:
                return self._store[art_id]
            return None

    async def get_artifact(self, artifact_id: str) -> Optional[bytes]:
        async with self._lock:
            return self._store.get(artifact_id)

    async def get_meta(self, task_id: str) -> Optional[BinaryPayloadMeta]:
        async with self._lock:
            return self._meta.get(task_id)

    async def remove_payload(self, task_id: str) -> None:
        async with self._lock:
            self._store.pop(task_id, None)
            self._store.pop(f"art_in_{task_id}", None)
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
