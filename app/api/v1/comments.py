import uuid

from fastapi import APIRouter, status

from app.api.v1.params import Limit, Offset
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page
from app.services import comment_service

router = APIRouter(tags=["comments"])


@router.get("/tasks/{task_id}/comments")
def list_comments(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[CommentRead]:
    comments, total = comment_service.list_comments(db, user, task_id, limit, offset)
    return Page[CommentRead](items=comments, total=total, limit=limit, offset=offset)


@router.post("/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    task_id: uuid.UUID, data: CommentCreate, user: CurrentUser, db: DbSession
) -> CommentRead:
    return comment_service.add_comment(db, user, task_id, data)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    comment_service.delete_comment(db, user, comment_id)
