import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import AdminUser, CurrentUser, DbSession
from app.models import User
from app.schemas.common import Page
from app.schemas.user import PasswordChange, RoleUpdate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserRead)
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> User:
    return user_service.update_profile(db, user, data)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(data: PasswordChange, user: CurrentUser, db: DbSession) -> None:
    user_service.change_password(db, user, data)


@router.get("")
def list_users(
    _: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> Page[UserRead]:
    users, total = user_service.list_users(db, limit, offset)
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{user_id}/role", response_model=UserRead)
def change_user_role(user_id: uuid.UUID, data: RoleUpdate, admin: AdminUser, db: DbSession) -> User:
    return user_service.set_role(db, admin, user_id, data.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: uuid.UUID, admin: AdminUser, db: DbSession) -> None:
    user_service.deactivate_user(db, admin, user_id)
