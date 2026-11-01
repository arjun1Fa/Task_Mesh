"""Authentication and Role-Based Access Control (RBAC) for TaskMesh."""

import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from taskmesh.core.models import utc_now

logger = logging.getLogger("taskmesh.security.auth")


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ORCHESTRATOR_OPERATOR = "orchestrator_operator"
    WORKER_OPERATOR = "worker_operator"
    VIEWER = "viewer"


# Standard permission matrix
PERMISSIONS_MAP: Dict[UserRole, Set[str]] = {
    UserRole.SUPER_ADMIN: {
        "cluster.view",
        "cluster.manage",
        "nodes.view",
        "nodes.manage",
        "tasks.view",
        "tasks.submit",
        "tasks.retry",
        "tasks.cancel",
        "scheduler.view",
        "scheduler.configure",
        "system.configure",
        "users.view",
        "users.manage",
        "security.manage",
        "audit.view",
        "worker.view",
        "worker.manage",
        "dlq.view",
        "dlq.manage",
        "recovery.view",
        "recovery.manage",
        "health.view",
        "logs.view",
    },
    UserRole.ORCHESTRATOR_OPERATOR: {
        "cluster.view",
        "cluster.manage",
        "nodes.view",
        "nodes.manage",
        "tasks.view",
        "tasks.submit",
        "tasks.retry",
        "tasks.cancel",
        "scheduler.view",
        "scheduler.configure",
        "audit.view",
        "worker.view",
        "worker.manage",
        "dlq.view",
        "dlq.manage",
        "recovery.view",
        "recovery.manage",
        "health.view",
        "logs.view",
        "system.view",
    },
    UserRole.WORKER_OPERATOR: {
        "nodes.view",
        "tasks.view",
        "worker.view",
        "worker.manage",
        "logs.view",
        "health.view",
    },
    UserRole.VIEWER: {
        "cluster.view",
        "nodes.view",
        "tasks.view",
        "scheduler.view",
        "audit.view",
        "worker.view",
        "dlq.view",
        "recovery.view",
        "health.view",
        "logs.view",
    },
}


class User(BaseModel):
    id: str
    username: str
    role: UserRole
    node_scope: Optional[str] = None  # Specific node ID restriction for worker operators
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    node_scope: Optional[str] = None


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    node_scope: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class TokenPayload(BaseModel):
    username: str
    role: UserRole
    node_scope: Optional[str] = None
    permissions: List[str]
    exp: float


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100_000)
    return dk.hex(), salt_bytes.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Verifies a password against a stored PBKDF2 hash."""
    new_hash, _ = hash_password(password, salt=salt_hex)
    return hmac.compare_digest(new_hash, hash_hex)


class AuthManager:
    """Manages users, authentication tokens, sessions, and RBAC permissions."""

    def __init__(self, db_path: str = "taskmesh.db", token_secret: Optional[str] = None) -> None:
        self.db_path = db_path
        self.token_secret = token_secret or os.getenv("TASKMESH_TOKEN_SECRET", secrets.token_hex(32))
        self._active_sessions: Dict[str, TokenPayload] = {}
        self._init_db()
        self._bootstrap_admin()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        role TEXT NOT NULL,
                        node_scope TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        last_login TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize users table in {self.db_path}: {e}")

    def _bootstrap_admin(self) -> None:
        """Bootstraps the initial Super Admin account if no users exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                if count == 0:
                    admin_pass = os.getenv("TASKMESH_ADMIN_PASSWORD", "admin123")
                    pwd_hash, salt = hash_password(admin_pass)
                    now_str = utc_now().isoformat()
                    conn.execute("""
                        INSERT INTO users (id, username, password_hash, salt, role, node_scope, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """, ("user_admin_001", "admin", pwd_hash, salt, UserRole.SUPER_ADMIN.value, None, now_str))
                    conn.commit()
                    logger.info("Bootstrapped initial Super Admin account: 'admin'")
        except Exception as e:
            logger.error(f"Failed to bootstrap admin user: {e}")

    def authenticate(self, username: str, password: str) -> Optional[Tuple[User, str]]:
        """Authenticates user and generates an access token if valid."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, password_hash, salt, role, node_scope, is_active, created_at, last_login
                    FROM users WHERE username = ?
                """, (username,))
                row = cursor.fetchone()
                if not row:
                    return None

                uid, uname, pwd_hash, salt, role_str, node_scope, is_active, created_at_str, last_login_str = row
                if not bool(is_active):
                    logger.warning(f"Authentication failed: user {username} is inactive")
                    return None

                if not verify_password(password, pwd_hash, salt):
                    logger.warning(f"Authentication failed: invalid password for user {username}")
                    return None

                # Update last login
                now = utc_now()
                conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now.isoformat(), uid))
                conn.commit()

                user = User(
                    id=uid,
                    username=uname,
                    role=UserRole(role_str),
                    node_scope=node_scope,
                    is_active=True,
                    created_at=datetime.fromisoformat(created_at_str),
                    last_login=now,
                )

                token = self._generate_token(user)
                return user, token
        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}", exc_info=True)
            return None

    def _generate_token(self, user: User, expiry_seconds: int = 86400) -> str:
        """Generates a signed bearer session token."""
        token_id = secrets.token_hex(24)
        permissions = sorted(list(PERMISSIONS_MAP.get(user.role, set())))
        payload = TokenPayload(
            username=user.username,
            role=user.role,
            node_scope=user.node_scope,
            permissions=permissions,
            exp=time.time() + expiry_seconds,
        )
        self._active_sessions[token_id] = payload
        return token_id

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validates bearer token and returns payload if active and unexpired."""
        payload = self._active_sessions.get(token)
        if not payload:
            return None
        if time.time() > payload.exp:
            self._active_sessions.pop(token, None)
            return None
        return payload

    def revoke_token(self, token: str) -> None:
        """Revokes an active session token on logout."""
        self._active_sessions.pop(token, None)

    def check_permission(self, payload: TokenPayload, required_permission: str) -> bool:
        """Verifies if the token holds the required permission."""
        if payload.role == UserRole.SUPER_ADMIN:
            return True
        return required_permission in payload.permissions

    def check_node_access(self, payload: TokenPayload, target_node_id: str) -> bool:
        """Verifies if user has permission to view or manage a specific node."""
        if payload.role in (UserRole.SUPER_ADMIN, UserRole.ORCHESTRATOR_OPERATOR, UserRole.VIEWER):
            return True
        if payload.role == UserRole.WORKER_OPERATOR:
            if not payload.node_scope or payload.node_scope == target_node_id:
                return True
        return False

    def list_users(self) -> List[User]:
        """Returns all registered users."""
        users = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, role, node_scope, is_active, created_at, last_login
                    FROM users ORDER BY created_at ASC
                """)
                for row in cursor.fetchall():
                    uid, uname, role_str, node_scope, is_active, created_str, login_str = row
                    users.append(User(
                        id=uid,
                        username=uname,
                        role=UserRole(role_str),
                        node_scope=node_scope,
                        is_active=bool(is_active),
                        created_at=datetime.fromisoformat(created_str),
                        last_login=datetime.fromisoformat(login_str) if login_str else None,
                    ))
        except Exception as e:
            logger.error(f"Error listing users: {e}")
        return users

    def get_user_by_username(self, username: str) -> Optional[User]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, role, node_scope, is_active, created_at, last_login
                    FROM users WHERE username = ?
                """, (username,))
                row = cursor.fetchone()
                if not row:
                    return None
                uid, uname, role_str, node_scope, is_active, created_str, login_str = row
                return User(
                    id=uid,
                    username=uname,
                    role=UserRole(role_str),
                    node_scope=node_scope,
                    is_active=bool(is_active),
                    created_at=datetime.fromisoformat(created_str),
                    last_login=datetime.fromisoformat(login_str) if login_str else None,
                )
        except Exception as e:
            logger.error(f"Error getting user {username}: {e}")
            return None

    def create_user(self, req: UserCreate) -> User:
        pwd_hash, salt = hash_password(req.password)
        uid = f"user_{secrets.token_hex(6)}"
        now = utc_now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO users (id, username, password_hash, salt, role, node_scope, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (uid, req.username, pwd_hash, salt, req.role.value, req.node_scope, now.isoformat()))
            conn.commit()

        return User(
            id=uid,
            username=req.username,
            role=req.role,
            node_scope=req.node_scope,
            is_active=True,
            created_at=now,
        )

    def update_user(self, username: str, req: UserUpdate) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user:
            return None

        updates = []
        params = []
        if req.role is not None:
            updates.append("role = ?")
            params.append(req.role.value)
            user.role = req.role
        if req.node_scope is not None:
            updates.append("node_scope = ?")
            params.append(req.node_scope if req.node_scope != "" else None)
            user.node_scope = req.node_scope if req.node_scope != "" else None
        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if req.is_active else 0)
            user.is_active = req.is_active
        if req.password:
            pwd_hash, salt = hash_password(req.password)
            updates.append("password_hash = ?, salt = ?")
            params.extend([pwd_hash, salt])

        if updates:
            params.append(username)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE username = ?", params)
                conn.commit()

        return user

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            return False  # Protect primary admin
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            return cursor.rowcount > 0

