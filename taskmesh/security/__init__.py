"""Security package for TaskMesh."""

from taskmesh.security.auth import (
    AuthManager,
    TokenPayload,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
    hash_password,
    verify_password,
    PERMISSIONS_MAP,
)
from taskmesh.security.audit import (
    AuditEvent,
    AuditLogger,
)
from taskmesh.security.hmac_auth import (
    SecurityManager,
    compute_hmac_signature,
    verify_hmac_signature,
)

__all__ = [
    "AuthManager",
    "TokenPayload",
    "User",
    "UserCreate",
    "UserRole",
    "UserUpdate",
    "hash_password",
    "verify_password",
    "PERMISSIONS_MAP",
    "AuditEvent",
    "AuditLogger",
    "SecurityManager",
    "compute_hmac_signature",
    "verify_hmac_signature",
]
