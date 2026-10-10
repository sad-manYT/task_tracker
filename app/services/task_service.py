import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from app.models import Category, ProjectMember, Task, User
from app.models.enums import ProjectRole, TaskPriority
from app.schemas.task import SortOrder, TaskCreate, TaskQuery, TaskSortField, TaskUpdate
from app.services.project_service import get_membership, get_project_for_user, has_role

PRIORITY_ORDER = case(
    {
        TaskPriority.LOW: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.HIGH: 3,
        TaskPriority.CRITICAL: 4,
    },
    value=Task.priority,
)

SORT_COLUMNS = {
    TaskSortField.CREATED_AT: Task.created_at,
    TaskSortField.DEADLINE: Task.deadline,
    TaskSortField.PRIORITY: PRIORITY_ORDER,
    TaskSortField.TITLE: Task.title,
}


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


def list_tasks(db: Session, user: User, query: TaskQuery) -> tuple[list[Task], int]:
    statement = select(Task).join(
        ProjectMember,
        and_(ProjectMember.project_id == Task.project_id, ProjectMember.user_id == user.id),
    )
    if query.project_id is not None:
        statement = statement.where(Task.project_id == query.project_id)
    if query.status is not None:
        statement = statement.where(Task.status == query.status)
    if query.priority is not None:
        statement = statement.where(Task.priority == query.priority)
    if query.assignee_id is not None:
        statement = statement.where(Task.assignee_id == query.assignee_id)
    if query.search is not None:
        statement = statement.where(Task.title.icontains(query.search, autoescape=True))

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0

    column = SORT_COLUMNS[query.sort_by]
    ordering = column.asc() if query.order == SortOrder.ASC else column.desc()
    statement = (
        statement.order_by(ordering.nulls_last(), Task.id).limit(query.limit).offset(query.offset)
    )
    return list(db.scalars(statement)), total
