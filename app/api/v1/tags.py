import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.v1.params import Limit, Offset
from app.core.dependencies import CurrentUser, DbSession
from app.models import Tag, Task
from app.schemas.common import Page, SearchText
from app.schemas.tag import TagCreate, TagRead, TaskTagAdd
from app.schemas.task import TaskRead
from app.services import tag_service

router = APIRouter(tags=["tags"])


@router.get("/tags")
def list_tags(
    _: CurrentUser,
    db: DbSession,
    search: Annotated[SearchText | None, Query()] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[TagRead]:
    tags, total = tag_service.list_tags(db, search, limit, offset)
    return Page[TagRead](
        items=[TagRead.model_validate(tag) for tag in tags],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagCreate, _: CurrentUser, db: DbSession) -> Tag:
    return tag_service.create_tag(db, data)


@router.post("/tasks/{task_id}/tags", response_model=TaskRead)
def add_tag_to_task(task_id: uuid.UUID, data: TaskTagAdd, user: CurrentUser, db: DbSession) -> Task:
    return tag_service.add_tag_to_task(db, user, task_id, data.tag_id)


@router.delete("/tasks/{task_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_task(
    task_id: uuid.UUID, tag_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> None:
    tag_service.remove_tag_from_task(db, user, task_id, tag_id)
