import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.models import Task
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, user: CurrentUser, db: DbSession) -> Task:
    return task_service.create_task(db, user, data)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Task:
    task, _ = task_service.get_task_for_user(db, task_id, user)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: uuid.UUID, data: TaskUpdate, user: CurrentUser, db: DbSession) -> Task:
    return task_service.update_task(db, user, task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    task_service.delete_task(db, user, task_id)
