import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models import Comment
from app.schemas.common import CommentBody, StrictModel


class CommentCreate(StrictModel):
    body: CommentBody


class CommentRead(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    author_username: str
    body: str
    created_at: datetime

    @classmethod
    def build(cls, comment: Comment, author_username: str) -> "CommentRead":
        return cls(
            id=comment.id,
            task_id=comment.task_id,
            author_id=comment.author_id,
            author_username=author_username,
            body=comment.body,
            created_at=comment.created_at,
        )
