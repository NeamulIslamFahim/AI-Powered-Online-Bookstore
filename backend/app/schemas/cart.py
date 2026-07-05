from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.book import BookResponse
from app.schemas.common import ORMBase


class CartItemCreate(BaseModel):
    book_id: int
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    book_id: int
    quantity: int = Field(gt=0)


class CartItemResponse(ORMBase):
    id: int
    quantity: int
    book: BookResponse
    subtotal: float


class CartResponse(ORMBase):
    id: int
    user_id: int
    created_at: datetime
    items: list[CartItemResponse]
    subtotal: float

