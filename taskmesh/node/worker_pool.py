"""Node worker pool and task handler execution."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import inspect
import time
from typing import Any, Callable, Dict, Optional

from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import CheckpointData, TaskResult, utc_now
from taskmesh.protocol.messages import TaskAssignmentPayload


class WorkerPool:
    """Async worker pool managing local task execution on a compute node."""

    def __init__(self, concurrency: int = 4) -> None:
        self.concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        self._thread_pool = ThreadPoolExecutor(max_workers=concurrency)
        self._running_tasks: Dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self._handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()

    def register_handler(self, task_type: str, handler: Callable) -> None:
        self._handlers[task_type] = handler

    def has_handler(self, task_type: str) -> bool:
        return task_type in self._handlers

    def get_supported_handlers(self) -> list[str]:
        return list(self._handlers.keys())

    @property
    def active_count(self) -> int:
        return len(self._running_tasks)

    async def execute_assignment(
        self,
        assignment: TaskAssignmentPayload,
        node_id: str,
        progress_callback: Optional[Callable[[float, str], Any]] = None,
        checkpoint_callback: Optional[Callable[[CheckpointData], Any]] = None,
        binary_payload: Optional[bytes] = None,
    ) -> TaskResult:
        """Executes assigned task under semaphore with timeout and cancellation support."""
        task_id = assignment.task_id
        attempt_id = assignment.attempt_id
        task_type = assignment.task_type

        handler = self._handlers.get(task_type)
        if not handler:
            return TaskResult(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=node_id,
                status=TaskStatus.FAILED,
                error=f"No local handler registered for task type '{task_type}'",
                completed_at=utc_now(),
            )

        start_time = time.perf_counter()

        async def _run() -> Any:
            async with self._semaphore:
                # Provide checkpoint, progress callback, and binary_payload if expected
                sig = inspect.signature(handler)
                kwargs = {}
                if "checkpoint_state" in sig.parameters:
                    kwargs["checkpoint_state"] = assignment.checkpoint_state
                if "progress_callback" in sig.parameters:
                    kwargs["progress_callback"] = progress_callback
                if "checkpoint_callback" in sig.parameters:
                    kwargs["checkpoint_callback"] = checkpoint_callback
                if "binary_payload" in sig.parameters:
                    kwargs["binary_payload"] = binary_payload

                if inspect.iscoroutinefunction(handler):
                    return await handler(assignment.payload, **kwargs)
                else:
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(
                        self._thread_pool,
                        lambda: handler(assignment.payload, **kwargs)
                    )

        coro = asyncio.wait_for(_run(), timeout=assignment.timeout_seconds)
        async_task = asyncio.create_task(coro)

        async with self._lock:
            self._running_tasks[task_id] = async_task

        try:
            output = await async_task
            elapsed = time.perf_counter() - start_time
            out_dict = output if isinstance(output, dict) else {"result": output}
            telemetry_metrics = {
                "inference_time_ms": out_dict.get("inference_time_ms", round(elapsed * 1000.0, 2)),
                "execution_time_seconds": round(elapsed, 4),
                "node_id": node_id,
                "attempt_id": attempt_id,
            }
            if binary_payload:
                telemetry_metrics["payload_size_bytes"] = len(binary_payload)

            return TaskResult(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=node_id,
                status=TaskStatus.COMPLETED,
                output=out_dict,
                metrics=telemetry_metrics,
                execution_time_seconds=round(elapsed, 4),
                completed_at=utc_now(),
            )

        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start_time
            return TaskResult(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=node_id,
                status=TaskStatus.FAILED,
                error=f"Task execution timed out after {assignment.timeout_seconds}s",
                execution_time_seconds=round(elapsed, 4),
                completed_at=utc_now(),
            )
        except asyncio.CancelledError:
            elapsed = time.perf_counter() - start_time
            return TaskResult(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=node_id,
                status=TaskStatus.CANCELLED,
                error="Task was cancelled",
                execution_time_seconds=round(elapsed, 4),
                completed_at=utc_now(),
            )
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return TaskResult(
                task_id=task_id,
                attempt_id=attempt_id,
                node_id=node_id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time_seconds=round(elapsed, 4),
                completed_at=utc_now(),
            )
        finally:
            async with self._lock:
                self._running_tasks.pop(task_id, None)

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            running = self._running_tasks.get(task_id)
            if running and not running.done():
                running.cancel()
                return True
            return False

    async def shutdown(self) -> None:
        async with self._lock:
            for task in self._running_tasks.values():
                if not task.done():
                    task.cancel()
        self._thread_pool.shutdown(wait=False)
