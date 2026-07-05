from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.schemas.book import BookCreate, BookResponse, BookUpdate, PaginatedBooks
from app.services.book_service import create_book, delete_book, get_book_by_id, list_books, update_book

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("", response_model=PaginatedBooks)
def get_books(
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=100),
    search: str | None = None,
    category: int | None = None,
    sort: str = "newest",
    db: Session = Depends(get_db),
):
    return list_books(db, page=page, limit=limit, search=search, category=category, sort=sort)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return get_book_by_id(db, book_id)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create(payload: BookCreate, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return create_book(db, payload)


@router.put("/{book_id}", response_model=BookResponse)
def update(book_id: int, payload: BookUpdate, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return update_book(db, book_id, payload)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(book_id: int, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    delete_book(db, book_id)

