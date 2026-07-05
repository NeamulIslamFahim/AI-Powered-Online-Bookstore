from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.schemas.book import BookCreate, BookUpdate
from app.utils.pagination import build_pagination


def _hydrate_book_defaults(db: Session, book: Book) -> Book:
    if book.category is None:
        fallback_category = db.query(Category).order_by(Category.id.asc()).first()
        if fallback_category:
            if book.category_id is None:
                book.category_id = fallback_category.id
            book.category = fallback_category
    return book


def list_books(db: Session, *, page: int, limit: int, search: str | None, category: int | None, sort: str):
    sales_quantity = func.coalesce(func.sum(OrderItem.quantity), 0)
    query = (
        db.query(Book, sales_quantity.label("sales_count"))
        .options(joinedload(Book.category))
        .outerjoin(OrderItem, OrderItem.book_id == Book.id)
        .group_by(Book.id)
    )

    if search:
        query = query.filter(or_(Book.title.ilike(f"%{search}%"), Book.author.ilike(f"%{search}%")))
    if category:
        query = query.filter(Book.category_id == category)

    if sort == "price_asc":
        query = query.order_by(Book.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Book.price.desc())
    elif sort == "oldest":
        query = query.order_by(Book.created_at.asc())
    elif sort == "best_selling":
        query = query.order_by(sales_quantity.desc(), Book.created_at.desc())
    else:
        query = query.order_by(Book.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * limit).limit(limit).all()
    books = []
    for book, sales_count in rows:
        _hydrate_book_defaults(db, book)
        avg = db.query(func.avg(Review.rating)).filter(Review.book_id == book.id).scalar()
        book.average_rating = round(float(avg), 1) if avg else 0
        book.sales_count = int(sales_count or 0)
        books.append(book)

    pagination = build_pagination(total=total, page=page, limit=limit)
    return {"items": books, "total": total, "page": page, "pages": pagination["pages"], "pagination": pagination}


def get_book_by_id(db: Session, book_id: int):
    book = db.query(Book).options(joinedload(Book.category)).filter(Book.id == book_id).first()
    if not book:
        raise AppException(404, "Book not found")
    _hydrate_book_defaults(db, book)
    avg = db.query(func.avg(Review.rating)).filter(Review.book_id == book.id).scalar()
    book.average_rating = round(float(avg), 1) if avg else 0
    return book


def create_book(db: Session, payload: BookCreate):
    if not db.query(Category).filter(Category.id == payload.category_id).first():
        raise AppException(404, "Category not found")
    if payload.isbn and db.query(Book).filter(Book.isbn == payload.isbn).first():
        raise AppException(400, "A book with this ISBN already exists")
    book = Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return get_book_by_id(db, book.id)


def update_book(db: Session, book_id: int, payload: BookUpdate):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise AppException(404, "Book not found")
    if not db.query(Category).filter(Category.id == payload.category_id).first():
        raise AppException(404, "Category not found")
    if payload.isbn:
        existing = db.query(Book).filter(Book.isbn == payload.isbn, Book.id != book_id).first()
        if existing:
            raise AppException(400, "A book with this ISBN already exists")
    for field, value in payload.model_dump().items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return get_book_by_id(db, book.id)


def delete_book(db: Session, book_id: int):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise AppException(404, "Book not found")

    pending_order_exists = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.book_id == book_id, Order.status.in_(["pending", "paid", "shipped"]))
        .first()
    )
    if pending_order_exists:
        raise AppException(400, "Cannot delete book with active orders")

    db.delete(book)
    db.commit()
