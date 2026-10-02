import enum

from sqlalchemy import CheckConstraint, Enum


def enum_column(enum_cls: type[enum.StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda cls: [item.value for item in cls],
        validate_strings=True,
    )


def enum_check(column: str, enum_cls: type[enum.StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{item.value}'" for item in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_values")
