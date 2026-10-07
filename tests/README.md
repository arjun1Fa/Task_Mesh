# TaskMesh Test Suite

TaskMesh uses `pytest` and `pytest-asyncio` for comprehensive unit and distributed integration testing.

## Running Tests

Run all unit and integration tests:
```bash
pytest tests/ -v
```

## Test Structure
- `tests/test_core_models.py`: Task lifecycle, attempt generation, validation, and lease expiration.
- `tests/test_priority_queue.py`: Priority ordering and FIFO tie-breaking stability.
- `tests/test_adaptive_pipeline.py`: Base scoring, EWMA dynamic multiplier, DRR fairness, MWU weights, and Q-learning.
- `tests/test_worker_pool.py`: Concurrent task execution, async/sync handlers, timeouts, and cancellation.
- `tests/test_retry_and_dlq.py`: Exponential backoff with jitter, retry exhaustion, and Dead-Letter Queue recovery.
- `tests/test_eligibility.py`: Hardware eligibility filtering (GPU, RAM, tags) and checkpoint management.
- `tests/test_api_endpoints.py`: FastAPI REST API task lifecycle and cluster health inspection.
- `tests/test_distributed_flow.py`: Full multi-node distributed task dispatching, WebSocket reporting, and automated node failure recovery.
