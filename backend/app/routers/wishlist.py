from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.wishlist import WishlistCreate, WishlistResponse
from app.services.wishlist_service import add_to_wishlist, get_wishlist, remove_from_wishlist

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=list[WishlistResponse])
def wishlist(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_wishlist(db, current_user)


@router.post("/add", response_model=list[WishlistResponse], status_code=status.HTTP_201_CREATED)
def add(payload: WishlistCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return add_to_wishlist(db, current_user, payload.book_id)


@router.delete("/remove/{book_id}", response_model=list[WishlistResponse])
def remove(book_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return remove_from_wishlist(db, current_user, book_id)

