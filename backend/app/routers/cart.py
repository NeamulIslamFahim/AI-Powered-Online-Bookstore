from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse
from app.services.cart_service import add_item_to_cart, clear_cart_items, get_or_create_cart, remove_cart_item, update_cart_item

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
def get_cart(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_or_create_cart(db, current_user)


@router.post("/add", response_model=CartResponse)
def add_to_cart(payload: CartItemCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return add_item_to_cart(db, current_user, book_id=payload.book_id, quantity=payload.quantity)


@router.put("/update", response_model=CartResponse)
def update_item(payload: CartItemUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return update_cart_item(db, current_user, book_id=payload.book_id, quantity=payload.quantity)


@router.delete("/remove/{book_id}", response_model=CartResponse)
def remove_item(book_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return remove_cart_item(db, current_user, book_id=book_id)


@router.delete("/clear", response_model=CartResponse)
def clear_items(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return clear_cart_items(db, current_user)

