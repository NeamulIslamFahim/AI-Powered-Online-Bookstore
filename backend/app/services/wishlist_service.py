from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.user import User
from app.models.wishlist import Wishlist


def get_wishlist(db: Session, user: User):
    return (
        db.query(Wishlist)
        .options(joinedload(Wishlist.book).joinedload(Book.category))
        .filter(Wishlist.user_id == user.id)
        .all()
    )


def add_to_wishlist(db: Session, user: User, book_id: int):
    if not db.query(Book).filter(Book.id == book_id).first():
        raise AppException(404, "Book not found")
    if db.query(Wishlist).filter(Wishlist.user_id == user.id, Wishlist.book_id == book_id).first():
        raise AppException(400, "Book already in wishlist")
    item = Wishlist(user_id=user.id, book_id=book_id)
    db.add(item)
    db.commit()
    return get_wishlist(db, user)


def remove_from_wishlist(db: Session, user: User, book_id: int):
    item = db.query(Wishlist).filter(Wishlist.user_id == user.id, Wishlist.book_id == book_id).first()
    if not item:
        raise AppException(404, "Wishlist item not found")
    db.delete(item)
    db.commit()
    return get_wishlist(db, user)
