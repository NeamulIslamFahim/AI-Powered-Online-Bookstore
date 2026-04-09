from pydantic import BaseModel
from app.schemas.order import OrderResponse


class AssistantChatRequest(BaseModel):
    chatInput: str
    sessionId: str


class AssistantOrderCreate(BaseModel):
    sessionId: str
    book: str | None = None
    quantity: int | None = None
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class AssistantOrderResponse(BaseModel):
    order_id: int
    book: str
    quantity: int
    total: float
    status: str
    order: OrderResponse | None = None


class AssistantChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    status: str | None = None
    sessionId: str | None = None
    timestamp: str | None = None
    tokenUsage: dict | None = None
