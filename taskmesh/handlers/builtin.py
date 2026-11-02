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


async def echo_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Echo workload returning submitted payload and verification echo."""
    return {
        "status": "echoed",
        "message": payload.get("message", "TaskMesh Echo"),
        "received_payload": payload,
        "timestamp": time.time(),
    }


def cpu_test_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """CPU intensive computational workload (runs in thread pool)."""
    iterations = int(payload.get("iterations", 50000))
    total = 0.0
    start = time.perf_counter()
    for i in range(1, iterations + 1):
        total += math.sqrt(i) * math.sin(i)
    elapsed = time.perf_counter() - start
    elapsed_rounded = round(elapsed, 4)
    checksum_val = round(total, 4)
    return {
        "iterations": iterations,
        "requested_iterations": iterations,
        "actual_iterations": iterations,
        "checksum": checksum_val,
        "computation_time_seconds": elapsed_rounded,
        "computation_duration": elapsed_rounded,
        "execution_duration": elapsed_rounded,
    }


def matrix_multiply_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Square matrix multiplication benchmark (runs in thread pool)."""
    dim = min(int(payload.get("dim", 64)), 256)
    start = time.perf_counter()
    a = [[float((i * 3 + j * 7) % 100) / 10.0 for j in range(dim)] for i in range(dim)]
    b = [[float((i * 5 + j * 2) % 100) / 10.0 for j in range(dim)] for i in range(dim)]
    c = [[0.0 for _ in range(dim)] for _ in range(dim)]
    for i in range(dim):
        for k in range(dim):
            for j in range(dim):
                c[i][j] += a[i][k] * b[k][j]
    elapsed = time.perf_counter() - start
    checksum = round(sum(sum(row) for row in c), 4)
    return {
        "dimension": dim,
        "checksum": checksum,
        "computation_time_seconds": round(elapsed, 4),
        "operations_count": dim * dim * dim * 2,
    }


def benchmark_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Generic compute benchmark."""
    steps = int(payload.get("steps", 10000))
    start = time.perf_counter()
    acc = 0.0
    for i in range(1, steps + 1):
        acc += math.log(i + 1) * math.cos(i)
    elapsed = time.perf_counter() - start
    return {
        "steps": steps,
        "checksum": round(acc, 4),
        "computation_time_seconds": round(elapsed, 4),
    }
