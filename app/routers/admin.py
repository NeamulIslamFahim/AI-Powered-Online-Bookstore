from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.schemas.order import AdminStatsResponse, OrderResponse, OrderStatusUpdate
from app.services.order_service import get_admin_stats, get_all_orders, update_order_status

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/orders", response_model=list[OrderResponse])
def admin_orders(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return get_all_orders(db)


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
def admin_update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return update_order_status(db, order_id, payload.status)


@router.get("/stats", response_model=AdminStatsResponse)
def stats(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return get_admin_stats(db, start_date=start_date, end_date=end_date)
