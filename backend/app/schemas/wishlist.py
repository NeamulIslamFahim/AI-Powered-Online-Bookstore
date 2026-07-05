from pydantic import BaseModel

from app.schemas.book import BookResponse
from app.schemas.common import ORMBase


class WishlistCreate(BaseModel):
    book_id: int


class WishlistResponse(ORMBase):
    id: int
    book: BookResponse
