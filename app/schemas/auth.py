from pydantic import BaseModel, Field

from app.schemas.common import Email, Password, StrictModel, Username


class RegisterRequest(StrictModel):
    email: Email
    username: Username
    password: Password


class LoginRequest(StrictModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=1, max_length=2048)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — это тип токена, а не пароль
