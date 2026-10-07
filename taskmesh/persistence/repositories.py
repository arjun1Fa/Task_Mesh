"""Persistence repositories for TaskMesh."""

import asyncio
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, List, Optional, Protocol

from taskmesh.core.enums import TaskStatus
from taskmesh.core.models import Task, TaskLease, utc_now


class TaskRepository(Protocol):
    """Abstract interface for task state persistence."""

    async def save(self, task: Task) -> None:
        ...

    async def get(self, task_id: str) -> Optional[Task]:
        ...

    async def list(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]:
        ...

    async def delete(self, task_id: str) -> bool:
        ...

    async def find_by_assigned_node(self, node_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        ...

    async def find_expired_leases(self, now: Optional[datetime] = None) -> List[Task]:
        ...


class MemoryTaskRepository:
    """Thread/async safe in-memory repository for unit tests and local runs."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, Task] = {}

    async def save(self, task: Task) -> None:
        async with self._lock:
            task.updated_at = utc_now()
            # Store a copy by model_dump / model_validate to prevent shared state mutation
            self._tasks[task.id] = Task.model_validate(task.model_dump())

    async def get(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                return Task.model_validate(task.model_dump())
            return None

    async def list(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]:
        async with self._lock:
            results = []
            for t in self._tasks.values():
                if status is None or t.status == status:
                    results.append(Task.model_validate(t.model_dump()))
                if len(results) >= limit:
                    break
            return results

    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            return self._tasks.pop(task_id, None) is not None

    async def find_by_assigned_node(self, node_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        async with self._lock:
            results = []
            for t in self._tasks.values():
                if t.assigned_node_id == node_id:
                    if status is None or t.status == status:
                        results.append(Task.model_validate(t.model_dump()))
            return results

    async def find_expired_leases(self, now: Optional[datetime] = None) -> List[Task]:
        async with self._lock:
            ref = now or utc_now()
            results = []
            for t in self._tasks.values():
                if t.status == TaskStatus.RUNNING and t.active_lease:
                    if t.active_lease.is_expired(ref):
                        results.append(Task.model_validate(t.model_dump()))
            return results


class SQLiteTaskRepository:
    """Persistent SQLite repository for single-node / orchestrator durable state."""

    def __init__(self, db_path: str = "taskmesh.db") -> None:
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assigned_node_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_node ON tasks(assigned_node_id)")
            conn.commit()

    async def save(self, task: Task) -> None:
        async with self._lock:
            task.updated_at = utc_now()
            raw_json = json.dumps(task.model_dump(mode="json"))
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO tasks (id, task_type, priority, status, assigned_node_id, created_at, updated_at, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        task_type=excluded.task_type,
                        priority=excluded.priority,
                        status=excluded.status,
                        assigned_node_id=excluded.assigned_node_id,
                        updated_at=excluded.updated_at,
                        data_json=excluded.data_json
                """, (
                    task.id,
                    task.task_type,
                    task.priority,
                    task.status.value,
                    task.assigned_node_id,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    raw_json
                ))
                conn.commit()

    async def get(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT data_json FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                data = json.loads(row[0])
                return Task.model_validate(data)

    async def list(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]:
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute(
                        "SELECT data_json FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT ?",
                        (status.value, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT data_json FROM tasks ORDER BY priority DESC, created_at ASC LIMIT ?",
                        (limit,)
                    )
                rows = cursor.fetchall()
                return [Task.model_validate(json.loads(r[0])) for r in rows]

    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                return cursor.rowcount > 0

    async def find_by_assigned_node(self, node_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        async with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute(
                        "SELECT data_json FROM tasks WHERE assigned_node_id = ? AND status = ?",
                        (node_id, status.value)
                    )
                else:
                    cursor.execute(
                        "SELECT data_json FROM tasks WHERE assigned_node_id = ?",
                        (node_id,)
                    )
                rows = cursor.fetchall()
                return [Task.model_validate(json.loads(r[0])) for r in rows]

    async def find_expired_leases(self, now: Optional[datetime] = None) -> List[Task]:
        ref = now or utc_now()
        running_tasks = await self.list(status=TaskStatus.RUNNING, limit=1000)
        return [t for t in running_tasks if t.active_lease and t.active_lease.is_expired(ref)]
