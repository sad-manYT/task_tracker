from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError
from app.core.security import hash_password, verify_password
from app.models import User
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
