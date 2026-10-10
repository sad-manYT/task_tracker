import uuid

from fastapi import APIRouter, status

from app.api.v1.params import Limit, Offset
from app.core.dependencies import CurrentUser, DbSession
from app.models.enums import ProjectRole
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(
    user: CurrentUser, db: DbSession, limit: Limit = 20, offset: Offset = 0
) -> Page[ProjectRead]:
    rows, total = project_service.list_projects(db, user, limit, offset)
    return Page[ProjectRead](
        items=[ProjectRead.build(project, role) for project, role in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession) -> ProjectRead:
    project = project_service.create_project(db, user, data)
    return ProjectRead.build(project, ProjectRole.OWNER)


@router.get("/{project_id}")
def get_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ProjectRead:
    project, role = project_service.get_project_for_user(db, project_id, user)
    return ProjectRead.build(project, role)


@router.patch("/{project_id}")
def update_project(
    project_id: uuid.UUID, data: ProjectUpdate, user: CurrentUser, db: DbSession
) -> ProjectRead:
    project, role = project_service.get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    return ProjectRead.build(project_service.update_project(db, project, data), role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    project, _ = project_service.get_project_for_user(db, project_id, user, ProjectRole.OWNER)
    project_service.delete_project(db, project)
