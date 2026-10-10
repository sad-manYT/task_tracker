import enum
import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import Description, SearchText, StrictModel, Title

MIN_DEADLINE_YEAR = 2000
MAX_DEADLINE_YEAR = 2100


def _check_deadline(value: datetime) -> datetime:
    if not MIN_DEADLINE_YEAR <= value.year <= MAX_DEADLINE_YEAR:
        raise ValueError(
            f"Дедлайн должен быть в пределах {MIN_DEADLINE_YEAR}–{MAX_DEADLINE_YEAR} годов"
        )
    if value <= datetime.now(UTC):
        raise ValueError("Дедлайн не может быть в прошлом")
    return value


Deadline = Annotated[AwareDatetime, AfterValidator(_check_deadline)]


class TaskCreate(StrictModel):
    project_id: uuid.UUID
    title: Title
    description: Description | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Deadline | None = None
    assignee_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None


class TaskUpdate(StrictModel):
    title: Title | None = None
    description: Description | None = None
    priority: TaskPriority | None = None
    deadline: Deadline | None = None
    category_id: uuid.UUID | None = None

    @field_validator("title", "priority")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Поле не может быть пустым")
        return value


class TaskStatusUpdate(StrictModel):
    status: TaskStatus


class TaskAssigneeUpdate(StrictModel):
    assignee_id: uuid.UUID | None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    creator_id: uuid.UUID
    assignee_id: uuid.UUID | None
    category_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskSortField(enum.StrEnum):
    CREATED_AT = "created_at"
    DEADLINE = "deadline"
    PRIORITY = "priority"
    TITLE = "title"


class SortOrder(enum.StrEnum):
    ASC = "asc"
    DESC = "desc"


class TaskQuery(StrictModel):
    project_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    search: SearchText | None = None
    sort_by: TaskSortField = TaskSortField.CREATED_AT
    order: SortOrder = SortOrder.DESC
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1_000_000)
