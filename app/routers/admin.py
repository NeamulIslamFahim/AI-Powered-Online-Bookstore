from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.schemas.order import AdminStatsResponse, OrderResponse, OrderStatusUpdate
from app.schemas.admin import AdminUserUpdate, AdminSessionResponse, AdminChatbotRequest, AdminChatbotResponse
from app.schemas.user import UserResponse
from app.services.order_service import get_admin_stats, get_all_orders, update_order_status
from app.services.admin_service import get_all_users, update_user_role, delete_user, get_all_sessions, delete_session
from app.services.admin_chat_service import process_admin_command

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


@router.get("/users", response_model=list[UserResponse])
def admin_users(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return get_all_users(db)


@router.put("/users/{user_id}/role", response_model=UserResponse)
def admin_update_user_role(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return update_user_role(db, user_id, payload.role)


@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    delete_user(db, user_id)
    return {"success": True}


@router.get("/sessions", response_model=list[AdminSessionResponse])
def admin_sessions(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return get_all_sessions(db)


@router.delete("/sessions/{session_id}")
def admin_delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    delete_session(db, session_id)
    return {"success": True}

@router.post("/assistant/chat", response_model=AdminChatbotResponse)
def admin_chatbot(
    payload: AdminChatbotRequest,
    _admin=Depends(get_current_admin),
):
    return process_admin_command(payload.message, session_id=payload.session_id)
