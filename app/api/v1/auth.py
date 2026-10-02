from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> User:
    return auth_service.register_user(db, data)


@router.post("/login")
def login(data: LoginRequest, db: DbSession) -> TokenPair:
    user = auth_service.authenticate(db, data.email, data.password)
    return auth_service.issue_tokens(db, user)


@router.post("/refresh")
def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    return auth_service.refresh_tokens(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: DbSession, user: CurrentUser) -> None:
    auth_service.logout(db, user, data.refresh_token)
