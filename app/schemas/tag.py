import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.common import StrictModel, TagName


class TagCreate(StrictModel):
    name: TagName


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class TaskTagAdd(StrictModel):
    tag_id: uuid.UUID
