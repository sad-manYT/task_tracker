import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.common import CategoryName, StrictModel


class CategoryCreate(StrictModel):
    project_id: uuid.UUID
    name: CategoryName


class CategoryUpdate(StrictModel):
    name: CategoryName


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
