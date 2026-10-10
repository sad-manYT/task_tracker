import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models import Project
from app.models.enums import ProjectRole
from app.schemas.common import Description, StrictModel, Title


class ProjectCreate(StrictModel):
    title: Title
    description: Description | None = None


class ProjectUpdate(StrictModel):
    title: Title | None = None
    description: Description | None = None

    @field_validator("title")
    @classmethod
    def title_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Название проекта не может быть пустым")
        return value


class ProjectRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    created_at: datetime
    my_role: ProjectRole

    @classmethod
    def build(cls, project: Project, role: ProjectRole) -> "ProjectRead":
        return cls(
            id=project.id,
            owner_id=project.owner_id,
            title=project.title,
            description=project.description,
            created_at=project.created_at,
            my_role=role,
        )
