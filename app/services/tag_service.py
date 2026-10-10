from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models import Tag
from app.schemas.tag import TagCreate

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
