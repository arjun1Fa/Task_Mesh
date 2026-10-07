"""Builtin generic task handlers."""

import asyncio
import math
import time
from typing import Any, Dict


async def log_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    message = payload.get("message", "TaskMesh log event")
    return {"status": "logged", "message": message, "timestamp": time.time()}


async def sleep_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    duration = float(payload.get("duration", 0.5))
    await asyncio.sleep(duration)
    return {"slept_seconds": duration}


def cpu_test_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """CPU intensive computational workload (runs in thread pool)."""
    iterations = int(payload.get("iterations", 50000))
    total = 0.0
    start = time.perf_counter()
    for i in range(1, iterations + 1):
        total += math.sqrt(i) * math.sin(i)
    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "checksum": round(total, 4),
        "computation_time_seconds": round(elapsed, 4),
    }
