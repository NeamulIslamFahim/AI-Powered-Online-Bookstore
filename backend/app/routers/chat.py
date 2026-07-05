from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session

from app.schemas.chat import AssistantChatRequest, AssistantChatResponse, AssistantOrderCreate, AssistantOrderResponse
from app.services.chat_service import place_assistant_order, send_message_to_assistant
from app.services.order_service import get_order_by_id

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return send_message_to_assistant(db, current_user, payload)


@router.post("/confirm-order", response_model=AssistantOrderResponse)
def assistant_confirm_order(
    payload: AssistantOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = place_assistant_order(db, current_user, payload)
    order = get_order_by_id(db, result["order_id"], user_id=current_user.id)
    return {**result, "order": order}
