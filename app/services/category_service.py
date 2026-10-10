import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models import Category, Task, User
from app.models.enums import ProjectRole
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.project_service import get_membership, get_project_for_user, has_role

MAX_CATEGORIES_PER_PROJECT = 50
CATEGORY_EXISTS_MESSAGE = "Категория с таким названием уже есть в проекте"


def get_category_for_user(
    db: Session,
    category_id: uuid.UUID,
    user: User,
    required_role: ProjectRole = ProjectRole.VIEWER,
) -> Category:
    category = db.get(Category, category_id)
    membership = get_membership(db, category.project_id, user.id) if category else None
    if category is None or membership is None:
        raise NotFoundError("Категория не найдена")
    if not has_role(membership.role, required_role):
        raise PermissionDeniedError("Недостаточно прав в этом проекте")
    return category


def _ensure_name_is_free(db: Session, project_id: uuid.UUID, name: str) -> None:
    exists = db.scalar(
        select(Category.id).where(
            Category.project_id == project_id,
            func.lower(Category.name) == name.lower(),
        )
    )
    if exists:
        raise ConflictError(CATEGORY_EXISTS_MESSAGE)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CATEGORY_EXISTS_MESSAGE) from None


def list_categories(db: Session, user: User, project_id: uuid.UUID) -> list[Category]:
    get_project_for_user(db, project_id, user)
    return list(
        db.scalars(
            select(Category).where(Category.project_id == project_id).order_by(Category.name)
        )
    )


def create_category(db: Session, user: User, data: CategoryCreate) -> Category:
    get_project_for_user(db, data.project_id, user, ProjectRole.EDITOR)
    count = db.scalar(
        select(func.count()).select_from(Category).where(Category.project_id == data.project_id)
    )
    if count is not None and count >= MAX_CATEGORIES_PER_PROJECT:
        raise BadRequestError(
            f"В проекте не может быть больше {MAX_CATEGORIES_PER_PROJECT} категорий"
        )
    _ensure_name_is_free(db, data.project_id, data.name)

    category = Category(project_id=data.project_id, name=data.name)
    db.add(category)
    _commit(db)
    db.refresh(category)
    return category


def rename_category(
    db: Session, user: User, category_id: uuid.UUID, data: CategoryUpdate
) -> Category:
    category = get_category_for_user(db, category_id, user, ProjectRole.EDITOR)
    if data.name.lower() != category.name.lower():
        _ensure_name_is_free(db, category.project_id, data.name)

    category.name = data.name
    _commit(db)
    db.refresh(category)
    return category


def delete_category(db: Session, user: User, category_id: uuid.UUID) -> None:
    category = get_category_for_user(db, category_id, user, ProjectRole.EDITOR)
    db.execute(update(Task).where(Task.category_id == category.id).values(category_id=None))
    db.delete(category)
    db.commit()
