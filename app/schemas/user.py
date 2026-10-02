import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole
from app.schemas.common import Email, Password, StrictModel, Username


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(StrictModel):
    email: Email | None = None
    username: Username | None = None


class PasswordChange(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class RoleUpdate(StrictModel):
    role: UserRole
