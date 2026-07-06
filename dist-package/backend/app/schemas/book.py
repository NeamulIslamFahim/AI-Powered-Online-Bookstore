from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.category import CategoryResponse
from app.schemas.common import ORMBase


class BookBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    author: str = Field(min_length=2, max_length=255)
    description: str | None = None
    price: float = Field(gt=0)
    stock_quantity: int = Field(ge=0)
    category_id: int
    image_url: str | None = None
    isbn: str | None = None
    published_date: date | None = None


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class BookResponse(ORMBase):
    id: int
    title: str
    author: str
    description: str | None = None
    price: float
    stock_quantity: int
    category_id: int | None = None
    image_url: str | None = None
    isbn: str | None = None
    published_date: date | None = None
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse | None = None
    average_rating: float | None = 0
    sales_count: int | None = 0


class PaginatedBooks(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    pages: int
    pagination: dict
