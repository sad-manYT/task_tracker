import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Tag, Task, User
from app.models.enums import ProjectRole
from app.schemas.tag import TagCreate
from app.services.task_service import get_task_for_user

MAX_TAGS_PER_TASK = 10
TAG_EXISTS_MESSAGE = "Такой тег уже существует"


def list_tags(db: Session, search: str | None, limit: int, offset: int) -> tuple[list[Tag], int]:
    statement = select(Tag)
    if search is not None:
        statement = statement.where(Tag.name.icontains(search, autoescape=True))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    tags = db.scalars(statement.order_by(Tag.name).limit(limit).offset(offset))
    return list(tags), total


def create_tag(db: Session, data: TagCreate) -> Tag:
    if db.scalar(select(Tag.id).where(Tag.name == data.name)):
        raise ConflictError(TAG_EXISTS_MESSAGE)

    tag = Tag(name=data.name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(TAG_EXISTS_MESSAGE) from None
    db.refresh(tag)
    return tag


def add_tag_to_task(db: Session, user: User, task_id: uuid.UUID, tag_id: uuid.UUID) -> Task:
    task, _ = get_task_for_user(db, task_id, user, ProjectRole.EDITOR)
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("Тег не найден")
    if tag in task.tags:
        raise ConflictError("Этот тег уже добавлен к задаче")
    if len(task.tags) >= MAX_TAGS_PER_TASK:
        raise BadRequestError(f"У задачи не может быть больше {MAX_TAGS_PER_TASK} тегов")

    task.tags.append(tag)
    db.commit()
    db.refresh(task)
    return task


def remove_tag_from_task(db: Session, user: User, task_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    task, _ = get_task_for_user(db, task_id, user, ProjectRole.EDITOR)
    tag = next((item for item in task.tags if item.id == tag_id), None)
    if tag is None:
        raise NotFoundError("Тег не привязан к задаче")

    task.tags.remove(tag)
    db.commit()
