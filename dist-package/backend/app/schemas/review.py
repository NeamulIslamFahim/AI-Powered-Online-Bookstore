from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase
from app.schemas.user import UserResponse


class ReviewCreate(BaseModel):
    book_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewResponse(ORMBase):
    id: int
    user_id: int
    book_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
    user: UserResponse

