from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class CategoryResponse(ORMBase):
    id: int
    name: str
    description: str | None = None

