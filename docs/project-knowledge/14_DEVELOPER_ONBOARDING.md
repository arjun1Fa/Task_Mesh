# TaskMesh — Developer Onboarding Guide

## 1. Welcome to TaskMesh

Welcome to the TaskMesh development team! This guide is designed to take an engineer with no prior knowledge of TaskMesh and make them a productive, confident contributor on Day 1.

---

## 2. Day 1 Suggested Learning Plan

| Time Window | Focus Area | Recommended Actions & Files to Read |
|---|---|---|
| **09:00 – 10:30** | **System Architecture & Foundations** | Read [`00_EXECUTIVE_OVERVIEW.md`](file:///C:/Malenia/TASK_MESH/docs/project-knowledge/00_EXECUTIVE_OVERVIEW.md) and [`02_SYSTEM_ARCHITECTURE.md`](file:///C:/Malenia/TASK_MESH/docs/project-knowledge/02_SYSTEM_ARCHITECTURE.md). Inspect domain models in [`taskmesh/core/models.py`](file:///C:/Malenia/TASK_MESH/taskmesh/core/models.py). |
| **10:30 – 11:30** | **Environment Setup & Local Cluster** | Follow [`11_SETUP_AND_EXECUTION_GUIDE.md`](file:///C:/Malenia/TASK_MESH/docs/project-knowledge/11_SETUP_AND_EXECUTION_GUIDE.md). Launch a 3-node cluster via `taskmesh-cluster --nodes 3`. Open web dashboard at `http://localhost:8000/`. |
| **11:30 – 12:30** | **CLI Hands-On & Task Tracing** | Submit tasks via `taskmeshctl task submit`. Inspect task JSON records and scheduler explainability logs (`taskmeshctl scheduler decisions`). |
| **13:30 – 15:00** | **Scheduling Pipeline Deep Dive** | Read [`04_SCHEDULING_ALGORITHMS.md`](file:///C:/Malenia/TASK_MESH/docs/project-knowledge/04_SCHEDULING_ALGORITHMS.md). Trace [`taskmesh/scheduler/adaptive.py`](file:///C:/Malenia/TASK_MESH/taskmesh/scheduler/adaptive.py) from `select_node()` through `record_task_outcome()`. |
| **15:00 – 16:30** | **Hands-On Exercise: Add a Custom Worker Handler** | Implement a new handler (e.g. `prime_factorization`), register it in `NodeAgent`, submit tasks, and verify execution. |
| **16:30 – 17:30** | **Run Test Suite & Debugging Exercise** | Execute `python -m pytest tests/ -v`. Walk through debugging a simulated node crash and lease expiration. |

---

## 3. Hands-On Developer Tutorials

### 3.1 Exercise 1: Adding a New Worker Capability / Task Handler

To add a new computational workload handler (e.g., a mathematical prime factorization handler):

#### Step 1: Define the Handler Function
Open [`taskmesh/handlers/builtin.py`](file:///C:/Malenia/TASK_MESH/taskmesh/handlers/builtin.py) and add:

```python
def prime_factor_handler(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Computes prime factors of a target integer."""
    n = int(payload.get("number", 100))
    factors = []
    d = 2
    temp = n
    start = time.perf_counter()
    while d * d <= temp:
        while (temp % d) == 0:
            factors.append(d)
            temp //= d
        d += 1
    if temp > 1:
        factors.append(temp)
    elapsed = time.perf_counter() - start

    return {
        "number": n,
        "prime_factors": factors,
        "computation_time_seconds": round(elapsed, 6),
    }
```

#### Step 2: Register Handler in `NodeAgent`
Open [`taskmesh/node/agent.py`](file:///C:/Malenia/TASK_MESH/taskmesh/node/agent.py). In `NodeAgent.__init__()`, register the handler:
```python
from taskmesh.handlers.builtin import prime_factor_handler
self.pool.register_handler("prime_factor", prime_factor_handler)
```

#### Step 3: Test Execution via CLI
Start the cluster and submit a test workload:
```bash
taskmeshctl task submit --type prime_factor --payload '{"number": 982451653}'
```
Query the task result:
```bash
taskmeshctl task get <TASK_ID>
```

---

### 3.2 Exercise 2: Introducing a New Scheduling Algorithm

To add an alternative scheduling algorithm (e.g. `RandomScheduler`):

#### Step 1: Implement the Scheduler Protocol
Create `RandomScheduler` inside [`taskmesh/scheduler/baseline.py`](file:///C:/Malenia/TASK_MESH/taskmesh/scheduler/baseline.py):

```python
import random

class RandomScheduler:
    """Randomly selects among eligible candidates."""

    async def select_node(self, task: Task, candidates: List[NodeProfile]) -> SchedulerDecision:
        eligible = filter_eligible_nodes(task, candidates)
        if not eligible:
            raise IneligibleNodeError(f"No eligible nodes available for task {task.id}")

        selected = random.choice(eligible)
        return SchedulerDecision(
            task_id=task.id,
            selected_node_id=selected.id,
            policy_used="random",
            candidate_node_ids=[n.id for n in eligible],
            candidate_scores={n.id: n.effective_score for n in eligible},
        )
```

#### Step 2: Register in `OrchestratorRuntime`
Open [`taskmesh/orchestrator/runtime.py`](file:///C:/Malenia/TASK_MESH/taskmesh/orchestrator/runtime.py) in `_init_scheduler()`:
```python
elif mode == "random":
    return RandomScheduler()
```

#### Step 3: Write an Automated Test
Add a test in [`tests/test_adaptive_pipeline.py`](file:///C:/Malenia/TASK_MESH/tests/test_adaptive_pipeline.py) verifying that `RandomScheduler.select_node()` returns a valid decision and never selects ineligible nodes.

---

## 4. How to Debug a Failed or Timed Out Task

When a task fails or remains in `PENDING`/`RETRYING`:

1. **Check Task Details via CLI**:
   ```bash
   taskmeshctl task get <TASK_ID>
   ```
   Inspect:
   - `status`: Is it `PENDING` (no eligible nodes), `RETRYING`, or `DLQ`?
   - `current_attempt` and `assigned_node_id`.
   - `error_message`: Contains the exact Python exception or timeout notice.
2. **Check Dead-Letter Queue (DLQ)**:
   ```bash
   taskmeshctl dlq list
   ```
   If a task exhausted its retries, recover it via:
   ```bash
   taskmeshctl dlq recover <TASK_ID>
   ```
3. **Inspect Scheduler Explainability Logs**:
   ```bash
   taskmeshctl scheduler decisions
   ```
   Examine why a node was chosen: inspect bids, candidate scores, DRR deficits, and wireless latency estimates.
4. **Inspect Node Agent & Orchestrator Logs**:
   Look for:
   - `Node [node-xxx] heartbeat timed out. Marking OFFLINE.`
   - `Discarding stale completed result for task ...`
   - `Rejected message from node: Missing HMAC signature`.

---

## 5. Contribution Guidelines & Safe Practices

1. **Never Break Backward Compatibility of Protocol Messages**:
   The WebSocket protocol envelope (`ProtocolMessage`) and payload schemas are versioned. Adding optional fields is safe; renaming or removing existing fields breaks live node agents.
2. **Preserve Database Decoupling**:
   Never write raw SQLite SQL queries inside `OrchestratorRuntime`. Always access data through the `TaskRepository` interface.
3. **Keep Heavy Dependencies Optional**:
   Never import `torch`, `ultralytics`, or `cv2` at the top level of core files (`taskmesh/core/`, `taskmesh/orchestrator/`, `taskmesh/scheduler/`). Always wrap them in local `try...except ImportError` blocks.
4. **Always Add Tests for Algorithmic Changes**:
   Any modification to `DRRFairnessManager`, `EWMAUpdater`, `MWUWeightLearner`, or `QLearningScheduler` must include unit tests and verify that `calculate_fairness_cv()` remains bounded.

