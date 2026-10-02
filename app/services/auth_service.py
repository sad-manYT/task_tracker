import secrets
import uuid
from functools import lru_cache

import jwt
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import RegisterRequest, TokenPair

INVALID_CREDENTIALS_MESSAGE = "Неверный email или пароль"
INVALID_REFRESH_MESSAGE = "Недействительный refresh-токен"
USER_EXISTS_MESSAGE = "Пользователь с таким email или именем уже существует"


@lru_cache
def _dummy_password_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def register_user(db: Session, data: RegisterRequest) -> User:
    exists = db.scalar(
        select(User.id).where(or_(User.email == data.email, User.username == data.username))
    )
    if exists:
        raise ConflictError(USER_EXISTS_MESSAGE)

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(USER_EXISTS_MESSAGE) from None
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, _dummy_password_hash())
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.InvalidTokenError:
        raise AuthenticationError(INVALID_REFRESH_MESSAGE) from None

    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if stored is None or str(stored.user_id) != payload["sub"]:
        raise AuthenticationError(INVALID_REFRESH_MESSAGE)

    if stored.revoked:
        revoke_all_user_tokens(db, stored.user_id)
        db.commit()
        raise AuthenticationError(INVALID_REFRESH_MESSAGE)

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(INVALID_REFRESH_MESSAGE)

    stored.revoked = True
    return issue_tokens(db, user)


def logout(db: Session, user: User, refresh_token: str) -> None:
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.user_id == user.id,
        )
    )
    if stored is not None and not stored.revoked:
        stored.revoked = True
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
