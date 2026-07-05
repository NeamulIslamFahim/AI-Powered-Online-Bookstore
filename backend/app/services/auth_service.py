from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin


def register_user(db: Session, payload: UserCreate) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise AppException(400, "Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, payload: UserLogin) -> str:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppException(401, "Invalid email or password")

    return create_access_token({"user_id": user.id, "role": user.role})

