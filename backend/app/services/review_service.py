from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.user import User


def _ensure_purchased(db: Session, user: User, book_id: int):
    purchased = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.user_id == user.id, OrderItem.book_id == book_id, Order.status.in_(["paid", "shipped", "delivered"]))
        .first()
    )
    if not purchased:
        raise AppException(400, "You can only review purchased books")


def get_reviews_for_book(db: Session, book_id: int):
    return (
        db.query(Review)
        .options(joinedload(Review.user))
        .filter(Review.book_id == book_id)
        .order_by(Review.created_at.desc())
        .all()
    )


def create_review(db: Session, user: User, *, book_id: int, rating: int, comment: str | None):
    if not db.query(Book).filter(Book.id == book_id).first():
        raise AppException(404, "Book not found")
    _ensure_purchased(db, user, book_id)
    if db.query(Review).filter(Review.user_id == user.id, Review.book_id == book_id).first():
        raise AppException(400, "You have already reviewed this book")
    review = Review(user_id=user.id, book_id=book_id, rating=rating, comment=comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return db.query(Review).options(joinedload(Review.user)).filter(Review.id == review.id).first()


def update_review(db: Session, user: User, *, review_id: int, rating: int, comment: str | None):
    review = db.query(Review).filter(Review.id == review_id, Review.user_id == user.id).first()
    if not review:
        raise AppException(404, "Review not found")
    review.rating = rating
    review.comment = comment
    db.commit()
    db.refresh(review)
    return db.query(Review).options(joinedload(Review.user)).filter(Review.id == review.id).first()


def delete_review(db: Session, user: User, review_id: int):
    review = db.query(Review).filter(Review.id == review_id, Review.user_id == user.id).first()
    if not review:
        raise AppException(404, "Review not found")
    db.delete(review)
    db.commit()
