"""Password hashing and session tokens. No FastAPI imports here."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config.settings import settings


def security_util_hash_password(plain: str) -> str:
    """Hash a password for storage.

    bcrypt generates a fresh salt each call, so the same password hashes to a
    different string every time. That is why verification re-hashes the attempt
    instead of comparing stored hashes.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def security_util_verify_password(plain: str, hashed: str) -> bool:
    """Check an attempt against a stored hash.

    The salt and cost live inside the stored hash, so checkpw can reproduce the
    original hashing exactly. Nothing is ever reversed.
    """
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # A malformed hash in the database must read as "wrong password"
        # rather than crash the login route.
        return False


def security_util_create_token(user_id: int, role: str) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def security_util_decode_token(token: str) -> dict[str, Any] | None:
    """Return the claims, or None if the token is invalid or expired.

    The signature is what makes the claims trustworthy: a user can read their
    role out of the token but cannot change it without invalidating it.
    """
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
