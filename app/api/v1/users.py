from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models import User
from app.schemas.user import PasswordChange, UserRead, UserUpdate
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
