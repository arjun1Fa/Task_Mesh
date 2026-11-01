"""Authentication and Role-Based Access Control (RBAC) for TaskMesh."""

import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
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
        self._mem_conn = sqlite3.connect(":memory:") if db_path == ":memory:" else None
        self.token_secret = token_secret or os.getenv("TASKMESH_TOKEN_SECRET", secrets.token_hex(32))
        self._active_sessions: Dict[str, TokenPayload] = {}
        self._init_db()
        self._bootstrap_admin()

    @contextmanager
    def _connect(self):
        if self._mem_conn is not None:
            yield self._mem_conn
        else:
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

    def _init_db(self) -> None:
        try:
            with self._connect() as conn:
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

                # Persistent user session storage
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        token_hash TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        role TEXT NOT NULL,
                        node_scope TEXT,
                        permissions TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at REAL NOT NULL,
                        is_revoked INTEGER NOT NULL DEFAULT 0
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(username)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
                # Prune expired or revoked sessions older than 24h
                conn.execute("DELETE FROM user_sessions WHERE expires_at < ? OR is_revoked = 1", (time.time() - 86400,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize users/sessions tables in {self.db_path}: {e}")

    def _bootstrap_admin(self) -> None:
        """Bootstraps the initial Super Admin account if no admin user exists."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                count = cursor.fetchone()[0]
                if count > 0:
                    return  # Administrator already bootstrapped; never overwrite existing admin

                env_pass = os.getenv("TASKMESH_ADMIN_PASSWORD")
                secret_file_created = None
                if env_pass:
                    admin_pass = env_pass
                else:
                    # Cryptographically random one-time bootstrap secret
                    admin_pass = secrets.token_urlsafe(16)
                    db_dir = os.path.dirname(os.path.abspath(self.db_path)) if self.db_path != ":memory:" else "."
                    secret_file = os.path.join(db_dir, ".admin_bootstrap_secret")
                    try:
                        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                        mode = 0o600
                        fd = os.open(secret_file, flags, mode)
                        with os.fdopen(fd, "w", encoding="utf-8") as f:
                            f.write(f"TASKMESH_ADMIN_PASSWORD={admin_pass}\n")
                            f.write("# ONE-TIME BOOTSTRAP CREDENTIAL. PLEASE ROTATE IMMEDIATELY AFTER INITIAL SETUP.\n")
                    except Exception:
                        with open(secret_file, "w", encoding="utf-8") as f:
                            f.write(f"TASKMESH_ADMIN_PASSWORD={admin_pass}\n")
                    secret_file_created = secret_file

                pwd_hash, salt = hash_password(admin_pass)
                now_str = utc_now().isoformat()
                conn.execute("""
                    INSERT INTO users (id, username, password_hash, salt, role, node_scope, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """, ("user_admin_001", "admin", pwd_hash, salt, UserRole.SUPER_ADMIN.value, None, now_str))
                conn.commit()

                if secret_file_created:
                    logger.warning("****************************************************************")
                    logger.warning("SECURITY ALERT: Initial Super Admin account 'admin' bootstrapped.")
                    logger.warning(f"One-time secret generated and saved to: {secret_file_created}")
                    logger.warning("File permissions set to private. Rotate this credential immediately!")
                    logger.warning("****************************************************************")
                else:
                    logger.info("Bootstrapped initial Super Admin account: 'admin' (from TASKMESH_ADMIN_PASSWORD)")

                # If demo accounts explicitly requested
                if os.getenv("TASKMESH_DEMO_ACCOUNTS", "false").lower() == "true":
                    op_pass = os.getenv("TASKMESH_OPERATOR_PASSWORD", "operator123")
                    view_pass = os.getenv("TASKMESH_VIEWER_PASSWORD", "viewer123")
                    op_hash, op_salt = hash_password(op_pass)
                    view_hash, view_salt = hash_password(view_pass)
                    conn.execute("""
                        INSERT OR IGNORE INTO users (id, username, password_hash, salt, role, node_scope, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """, ("user_operator_001", "operator", op_hash, op_salt, UserRole.ORCHESTRATOR_OPERATOR.value, None, now_str))
                    conn.execute("""
                        INSERT OR IGNORE INTO users (id, username, password_hash, salt, role, node_scope, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """, ("user_viewer_001", "viewer", view_hash, view_salt, UserRole.VIEWER.value, None, now_str))
                    conn.commit()
                    logger.info("Demo accounts bootstrapped: 'operator' and 'viewer'")
        except Exception as e:
            logger.error(f"Failed to bootstrap admin user: {e}", exc_info=True)

    def authenticate(self, username: str, password: str) -> Optional[Tuple[User, str]]:
        """Authenticates user and generates an access token if valid."""
        try:
            with self._connect() as conn:
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
        """Generates a signed bearer session token and persists it in SQLite."""
        token_id = secrets.token_hex(24)
        token_hash = hashlib.sha256(token_id.encode("utf-8")).hexdigest()
        permissions = sorted(list(PERMISSIONS_MAP.get(user.role, set())))
        now_ts = time.time()
        exp_ts = now_ts + expiry_seconds
        payload = TokenPayload(
            username=user.username,
            role=user.role,
            node_scope=user.node_scope,
            permissions=permissions,
            exp=exp_ts,
        )
        self._active_sessions[token_id] = payload

        # Persist session to SQLite
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO user_sessions (token_hash, username, role, node_scope, permissions, created_at, expires_at, is_revoked)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    token_hash,
                    user.username,
                    user.role.value,
                    user.node_scope,
                    json.dumps(permissions),
                    utc_now().isoformat(),
                    exp_ts,
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist user session to {self.db_path}: {e}")

        return token_id

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validates bearer token and returns payload if active and unexpired."""
        now_ts = time.time()
        # Fast memory check
        payload = self._active_sessions.get(token)
        if payload:
            if now_ts > payload.exp:
                self.revoke_token(token)
                return None
            return payload

        # Persistent session lookup (e.g. after orchestrator restart)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, role, node_scope, permissions, expires_at, is_revoked
                    FROM user_sessions WHERE token_hash = ?
                """, (token_hash,))
                row = cursor.fetchone()
                if not row:
                    return None

                username, role_str, node_scope, perms_json, exp_ts, is_revoked = row
                if bool(is_revoked) or now_ts > exp_ts:
                    return None

                # Also verify user is still active in users table
                cursor.execute("SELECT is_active FROM users WHERE username = ?", (username,))
                u_row = cursor.fetchone()
                if not u_row or not bool(u_row[0]):
                    return None

                permissions = json.loads(perms_json)
                payload = TokenPayload(
                    username=username,
                    role=UserRole(role_str),
                    node_scope=node_scope,
                    permissions=permissions,
                    exp=exp_ts,
                )
                self._active_sessions[token] = payload
                return payload
        except Exception as e:
            logger.error(f"Error querying persistent session: {e}")
            return None

    def revoke_token(self, token: str) -> None:
        """Revokes an active session token on logout."""
        self._active_sessions.pop(token, None)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        try:
            with self._connect() as conn:
                conn.execute("UPDATE user_sessions SET is_revoked = 1 WHERE token_hash = ?", (token_hash,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error revoking session: {e}")

    def revoke_all_user_sessions(self, username: str) -> None:
        """Revokes all active sessions for a given user (e.g. on password change)."""
        try:
            with self._connect() as conn:
                conn.execute("UPDATE user_sessions SET is_revoked = 1 WHERE username = ?", (username,))
                conn.commit()
            # Clear from in-memory cache
            evict = [t for t, p in self._active_sessions.items() if p.username == username]
            for t in evict:
                self._active_sessions.pop(t, None)
        except Exception as e:
            logger.error(f"Error revoking sessions for {username}: {e}")

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
            with self._connect() as conn:
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
            with self._connect() as conn:
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
        with self._connect() as conn:
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
            with self._connect() as conn:
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE username = ?", params)
                conn.commit()

        if req.password or req.is_active is False:
            self.revoke_all_user_sessions(username)

        return user

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            return False  # Protect primary admin
        self.revoke_all_user_sessions(username)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            return cursor.rowcount > 0

