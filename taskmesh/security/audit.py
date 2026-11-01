"""Audit logging subsystem for TaskMesh administrative and cluster events."""

import json
import logging
import sqlite3
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from taskmesh.core.models import utc_now

logger = logging.getLogger("taskmesh.security.audit")


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=utc_now)
    actor: str = "system"
    role: str = "system"
    action: str
    target: str = ""
    result: str = "success"  # "success", "denied", "error"
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """Records security, administrative, and configuration actions to a durable audit trail."""

    def __init__(self, db_path: str = "taskmesh.db", max_memory_records: int = 1000) -> None:
        self.db_path = db_path
        self._memory_buffer: deque = deque(maxlen=max_memory_records)
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target TEXT NOT NULL,
                        result TEXT NOT NULL,
                        details_json TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize audit_logs table: {e}")

    def log(
        self,
        action: str,
        actor: str = "system",
        role: str = "system",
        target: str = "",
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Records an audit event, sanitizing any sensitive parameters."""
        sanitized_details = self._sanitize(details or {})
        event = AuditEvent(
            action=action,
            actor=actor,
            role=role,
            target=target,
            result=result,
            details=sanitized_details,
        )

        self._memory_buffer.appendleft(event)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit_logs (id, timestamp, actor, role, action, target, result, details_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id,
                    event.timestamp.isoformat(),
                    event.actor,
                    event.role,
                    event.action,
                    event.target,
                    event.result,
                    json.dumps(event.details),
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")

        return event

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures secrets, passwords, and tokens are never written to audit logs."""
        clean = {}
        sensitive_keys = {"password", "token", "secret", "join_token", "hash", "salt", "signature"}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                clean[k] = "******"
            elif isinstance(v, dict):
                clean[k] = self._sanitize(v)
            else:
                clean[k] = v
        return clean

    def query(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Queries audit events matching filters."""
        results: List[AuditEvent] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT id, timestamp, actor, role, action, target, result, details_json FROM audit_logs WHERE 1=1"
                params = []
                if actor:
                    query += " AND actor = ?"
                    params.append(actor)
                if action:
                    query += " AND action = ?"
                    params.append(action)
                if result:
                    query += " AND result = ?"
                    params.append(result)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = conn.cursor()
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    eid, ts_str, act, rle, acn, tgt, res, dt_json = row
                    results.append(AuditEvent(
                        id=eid,
                        timestamp=datetime.fromisoformat(ts_str),
                        actor=act,
                        role=rle,
                        action=acn,
                        target=tgt,
                        result=res,
                        details=json.loads(dt_json) if dt_json else {},
                    ))
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            # Fallback to in-memory buffer
            results = list(self._memory_buffer)[:limit]

        return results

