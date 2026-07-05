from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.order import Order
from sqlalchemy import text

def get_all_users(db: Session):
    return db.query(User).order_by(User.id.desc()).all()

def update_user_role(db: Session, user_id: int, role: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ["admin", "customer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()

def get_all_sessions(db: Session):
    # Fetch assistant conversations
    rows = db.execute(
        text(
            """
            SELECT id, session_id, user_id, book_id, quantity, customer_name, phone, address, state, negotiated_unit_price, created_at, updated_at
            FROM assistant_conversations
            ORDER BY created_at DESC
            """
        )
    ).mappings().all()
    
    sessions = []
    for row in rows:
        user = db.query(User).filter(User.id == row["user_id"]).first()
        items = db.execute(
            text(
                """
                SELECT id, book_id, quantity, negotiated_unit_price
                FROM assistant_conversation_items
                WHERE session_id = :session_id AND user_id = :user_id
                """
            ),
            {"session_id": row["session_id"], "user_id": row["user_id"]}
        ).mappings().all()
        
        session_data = dict(row)
        session_data["user"] = user
        session_data["items"] = [dict(i) for i in items]
        sessions.append(session_data)
        
    return sessions

def delete_session(db: Session, session_id: str):
    db.execute(text("DELETE FROM assistant_conversation_items WHERE session_id = :session_id"), {"session_id": session_id})
    db.execute(text("DELETE FROM assistant_order_sessions WHERE session_id = :session_id"), {"session_id": session_id})
    db.execute(text("DELETE FROM assistant_conversations WHERE session_id = :session_id"), {"session_id": session_id})
    db.commit()
