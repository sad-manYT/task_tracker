import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models import Project, ProjectMember, User
from app.models.enums import ProjectRole
from app.schemas.project import ProjectCreate, ProjectUpdate

ROLE_LEVEL = {
    ProjectRole.VIEWER: 1,
    ProjectRole.EDITOR: 2,
    ProjectRole.OWNER: 3,
}


def has_role(role: ProjectRole, required: ProjectRole) -> bool:
    return ROLE_LEVEL[role] >= ROLE_LEVEL[required]


def get_membership(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectMember | None:
    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )


def get_project_for_user(
    db: Session,
    project_id: uuid.UUID,
    user: User,
    required_role: ProjectRole = ProjectRole.VIEWER,
) -> tuple[Project, ProjectRole]:
    project = db.get(Project, project_id)
    membership = get_membership(db, project_id, user.id) if project else None
    if project is None or membership is None:
        raise NotFoundError("Проект не найден")
    if not has_role(membership.role, required_role):
        raise PermissionDeniedError("Недостаточно прав в этом проекте")
    return project, membership.role


def create_project(db: Session, user: User, data: ProjectCreate) -> Project:
    project = Project(owner_id=user.id, **data.model_dump())
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER))
    db.commit()
    db.refresh(project)
    return project


def list_projects(
    db: Session, user: User, limit: int, offset: int
) -> tuple[list[tuple[Project, ProjectRole]], int]:
    query = (
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(Project.created_at.desc(), Project.id).limit(limit).offset(offset)
    )
    return [(project, role) for project, role in rows], total


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()
