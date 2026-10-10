import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from app.models import Category, Task, User
from app.models.enums import ProjectRole
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_service import get_membership, get_project_for_user, has_role


def get_task_for_user(
    db: Session,
    task_id: uuid.UUID,
    user: User,
    required_role: ProjectRole = ProjectRole.VIEWER,
) -> tuple[Task, ProjectRole]:
    task = db.get(Task, task_id)
    membership = get_membership(db, task.project_id, user.id) if task else None
    if task is None or membership is None:
        raise NotFoundError("Задача не найдена")
    if not has_role(membership.role, required_role):
        raise PermissionDeniedError("Недостаточно прав в этом проекте")
    return task, membership.role


def _check_assignee(db: Session, project_id: uuid.UUID, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is not None and get_membership(db, project_id, assignee_id) is None:
        raise BadRequestError("Исполнителем может быть только участник проекта")


def _check_category(db: Session, project_id: uuid.UUID, category_id: uuid.UUID | None) -> None:
    if category_id is None:
        return
    category = db.get(Category, category_id)
    if category is None or category.project_id != project_id:
        raise BadRequestError("Категория не найдена в этом проекте")


def create_task(db: Session, user: User, data: TaskCreate) -> Task:
    get_project_for_user(db, data.project_id, user, ProjectRole.EDITOR)
    _check_assignee(db, data.project_id, data.assignee_id)
    _check_category(db, data.project_id, data.category_id)

    task = Task(creator_id=user.id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, user: User, task_id: uuid.UUID, data: TaskUpdate) -> Task:
    task, _ = get_task_for_user(db, task_id, user, ProjectRole.EDITOR)
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        _check_category(db, task.project_id, changes["category_id"])

    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, user: User, task_id: uuid.UUID) -> None:
    task, _ = get_task_for_user(db, task_id, user, ProjectRole.EDITOR)
    db.delete(task)
    db.commit()
