from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.core.security import MAX_PASSWORD_BYTES


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_password_strength(value: str) -> str:
    if len(value.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError("Пароль слишком длинный")
    if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
        raise ValueError("Пароль должен содержать хотя бы одну букву и одну цифру")
    return value


Email = Annotated[EmailStr, AfterValidator(str.lower)]
Username = Annotated[str, Field(pattern=r"^[A-Za-z0-9_]{3,50}$")]
Password = Annotated[
    str, Field(min_length=8, max_length=72), AfterValidator(_check_password_strength)
]


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
