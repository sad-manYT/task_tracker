import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.schemas.user import PasswordChange, UserUpdate
from app.services.auth_service import revoke_all_user_tokens


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    changes = data.model_dump(exclude_none=True)

    if "email" in changes and changes["email"] != user.email:
        if db.scalar(select(User.id).where(User.email == changes["email"])):
            raise ConflictError("Этот email уже используется")
    if "username" in changes and changes["username"] != user.username:
        if db.scalar(select(User.id).where(User.username == changes["username"])):
            raise ConflictError("Это имя пользователя уже занято")

    for field, value in changes.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Email или имя пользователя уже используются") from None
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise BadRequestError("Текущий пароль указан неверно")
    if data.current_password == data.new_password:
        raise BadRequestError("Новый пароль должен отличаться от текущего")

    user.password_hash = hash_password(data.new_password)
    revoke_all_user_tokens(db, user.id)
    db.commit()


def list_users(db: Session, limit: int, offset: int) -> tuple[list[User], int]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    users = db.scalars(select(User).order_by(User.created_at, User.id).limit(limit).offset(offset))
    return list(users), total


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")
    return user


def set_role(db: Session, admin: User, user_id: uuid.UUID, role: UserRole) -> User:
    if user_id == admin.id:
        raise BadRequestError("Нельзя изменить собственную роль")
    user = get_user_or_404(db, user_id)
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, admin: User, user_id: uuid.UUID) -> None:
    if user_id == admin.id:
        raise BadRequestError("Нельзя деактивировать собственную учётную запись")
    user = get_user_or_404(db, user_id)
    user.is_active = False
    revoke_all_user_tokens(db, user.id)
    db.commit()
