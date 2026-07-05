from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.review_service import create_review, delete_review, get_reviews_for_book, update_review

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/book/{book_id}", response_model=list[ReviewResponse])
def reviews_for_book(book_id: int, db: Session = Depends(get_db)):
    return get_reviews_for_book(db, book_id)


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return create_review(db, current_user, book_id=payload.book_id, rating=payload.rating, comment=payload.comment)


@router.put("/{review_id}", response_model=ReviewResponse)
def update(review_id: int, payload: ReviewUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return update_review(db, current_user, review_id=review_id, rating=payload.rating, comment=payload.comment)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(review_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    delete_review(db, current_user, review_id)

