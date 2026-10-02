import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]

MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode()
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode())
    except ValueError:
        return False


def _create_token(user_id: uuid.UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, expires_delta: timedelta | None = None) -> str:
    delta = expires_delta or timedelta(minutes=get_settings().access_token_expire_minutes)
    return _create_token(user_id, "access", delta)


def create_refresh_token(
    user_id: uuid.UUID, expires_delta: timedelta | None = None
) -> tuple[str, datetime]:
    delta = expires_delta or timedelta(days=get_settings().refresh_token_expire_days)
    return _create_token(user_id, "refresh", delta), datetime.now(UTC) + delta


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "type", "exp", "iat", "jti"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Неверный тип токена")
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
