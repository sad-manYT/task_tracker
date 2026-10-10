import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[Category]:
    return category_service.list_categories(db, user, project_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, user: CurrentUser, db: DbSession) -> Category:
    return category_service.create_category(db, user, data)


@router.patch("/{category_id}", response_model=CategoryRead)
def rename_category(
    category_id: uuid.UUID, data: CategoryUpdate, user: CurrentUser, db: DbSession
) -> Category:
    return category_service.rename_category(db, user, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    category_service.delete_category(db, user, category_id)
