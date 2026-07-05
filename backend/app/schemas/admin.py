from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse

class AdminUserUpdate(BaseModel):
    role: str

class AdminSessionItemResponse(BaseModel):
    id: int
    book_id: int
    quantity: int | None
    negotiated_unit_price: float | None

class AdminSessionResponse(BaseModel):
    id: int
    session_id: str
    user_id: int
    user: UserResponse
    book_id: int | None
    quantity: int | None
    negotiated_unit_price: float | None
    customer_name: str | None
    phone: str | None
    address: str | None
    state: str
    created_at: datetime
    updated_at: datetime
    items: list[AdminSessionItemResponse]

class AdminChatbotRequest(BaseModel):
    message: str
    session_id: str = "default"
    image_url: str | None = None

class AdminChatbotResponse(BaseModel):
    action: str
    target: str | None
    reply: str
    image_url: str | None = None
