from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.order import OrderResponse
from app.services.order_service import checkout, get_order_by_id, get_orders_for_user

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/checkout", response_model=OrderResponse)
def checkout_order(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return checkout(db, current_user)


@router.get("/my", response_model=list[OrderResponse])
def my_orders(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_orders_for_user(db, current_user)


@router.get("/{order_id}", response_model=OrderResponse)
def order_details(order_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_order_by_id(db, order_id, user_id=current_user.id)

