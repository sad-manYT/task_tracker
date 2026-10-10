import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models import Comment, Task, User
from app.models.enums import ProjectRole
from app.schemas.comment import CommentCreate, CommentRead
from app.services.project_service import get_membership
from app.services.task_service import get_task_for_user


def list_comments(
    db: Session, user: User, task_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[CommentRead], int]:
    task, _ = get_task_for_user(db, task_id, user)
    total = (
        db.scalar(select(func.count()).select_from(Comment).where(Comment.task_id == task.id)) or 0
    )
    rows = db.execute(
        select(Comment, User.username)
        .join(User, User.id == Comment.author_id)
        .where(Comment.task_id == task.id)
        .order_by(Comment.created_at, Comment.id)
        .limit(limit)
        .offset(offset)
    )
    return [CommentRead.build(comment, username) for comment, username in rows], total


def add_comment(db: Session, user: User, task_id: uuid.UUID, data: CommentCreate) -> CommentRead:
    task, _ = get_task_for_user(db, task_id, user)
    comment = Comment(task_id=task.id, author_id=user.id, body=data.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentRead.build(comment, user.username)


def delete_comment(db: Session, user: User, comment_id: uuid.UUID) -> None:
    comment = db.get(Comment, comment_id)
    task = db.get(Task, comment.task_id) if comment else None
    membership = get_membership(db, task.project_id, user.id) if task else None
    if comment is None or membership is None:
        raise NotFoundError("Комментарий не найден")
    if comment.author_id != user.id and membership.role != ProjectRole.OWNER:
        raise PermissionDeniedError(
            "Удалить комментарий может только его автор или владелец проекта"
        )

    db.delete(comment)
    db.commit()
