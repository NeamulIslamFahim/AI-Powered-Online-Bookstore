from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib import error, request

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.book import Book
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.user import User
from app.schemas.chat import AssistantChatRequest, AssistantOrderCreate

GREETING_WORDS = {"hello", "hi", "hey", "assalamualaikum", "good morning", "good afternoon", "good evening"}
CONFIRM_WORDS = {"yes", "y", "confirm", "confirmed", "proceed", "ok", "okay"}
CANCEL_WORDS = {"cancel", "stop", "no", "nope", "not now"}
PLACE_ORDER_KEYWORDS = {
    "place order",
    "order now",
    "buy now",
    "make the order",
    "complete order",
    "checkout",
    "check out",
    "proceed with order",
    "go ahead with order",
}
CATEGORY_ALIASES = {
    "fiction": "Fiction",
    "non fiction": "Non Fiction",
    "non-fiction": "Non Fiction",
    "self improvement": "Self Improvement",
    "self-improvement": "Self Improvement",
    "business": "Business",
}
NEGOTIATION_KEYWORDS = {
    "discount",
    "less",
    "lower",
    "best price",
    "reduce",
    "cheap",
    "cheaper",
    "offer",
    "nego",
    "negotiate",
}
MAX_NEGOTIATION_DISCOUNT = 0.10
REVIEW_KEYWORDS = {
    "review",
    "reviews",
    "rating",
    "ratings",
    "feedback",
    "opinion",
    "opinions",
    "thoughts",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_webhook_reply(payload: dict) -> tuple[str | None, dict | None]:
    if not isinstance(payload, dict):
        return None, None

    reply = payload.get("reply") or payload.get("message") or payload.get("output")
    token_usage = payload.get("tokenUsage") if isinstance(payload.get("tokenUsage"), dict) else None

    if isinstance(reply, str) and reply.strip():
        return reply.strip(), token_usage

    data = payload.get("data")
    if isinstance(data, dict):
        reply = data.get("reply") or data.get("message") or data.get("output")
        token_usage = token_usage or (data.get("tokenUsage") if isinstance(data.get("tokenUsage"), dict) else None)
        if isinstance(reply, str) and reply.strip():
            return reply.strip(), token_usage

    return None, token_usage


def _try_n8n_assistant_reply(
    user: User,
    payload: AssistantChatRequest,
    *,
    state: str,
    current_book: Book | None,
    intent_hint: str,
) -> tuple[str | None, dict | None]:
    if not settings.N8N_CHAT_WEBHOOK_URL:
        return None, None

    request_body = {
        "chatInput": payload.chatInput,
        "sessionId": payload.sessionId,
        "temperature": settings.ASSISTANT_TEMPERATURE,
        "intentHint": intent_hint,
        "state": state,
        "timestamp": _now_iso(),
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "selectedBook": (
            {
                "id": current_book.id,
                "title": current_book.title,
                "author": current_book.author,
                "description": current_book.description,
                "price": float(current_book.price),
                "stock_quantity": current_book.stock_quantity,
            }
            if current_book
            else None
        ),
    }

    try:
        req = request.Request(
            settings.N8N_CHAT_WEBHOOK_URL,
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=12) as response:
            raw = response.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None, None

    return _extract_webhook_reply(parsed)


def _normalize(text_value: str) -> str:
    return re.sub(r"\s+", " ", text_value.strip().lower())


def _is_greeting(message: str) -> bool:
    normalized = _normalize(message)
    return normalized in GREETING_WORDS


def _is_confirmation(message: str) -> bool:
    normalized = _normalize(message)
    return normalized in CONFIRM_WORDS


def _is_cancellation(message: str) -> bool:
    normalized = _normalize(message)
    return normalized in CANCEL_WORDS


def _is_place_order_request(message: str) -> bool:
    normalized = _normalize(message)
    if any(keyword in normalized for keyword in PLACE_ORDER_KEYWORDS):
        return True
    return normalized in {"place it", "order it", "buy it"}


def _extract_quantity(message: str) -> int | None:
    match = re.search(r"\b(\d+)\b", message)
    if not match:
        return None
    return int(match.group(1))


def _extract_phone(message: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s-]{7,}\d)", message)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1))


def _extract_discount_percent(message: str) -> float | None:
    percent_match = re.search(r"(\d{1,2})(?:\s*)%", message)
    if percent_match:
        return int(percent_match.group(1)) / 100
    return None


def _extract_price_offer_amount(message: str) -> float | None:
    patterns = [
        r"\$\s*(\d+(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(?:dollar|dollars|usd)\b",
        r"(?:make it|give it|do it|can you do|can you make it)\s*(?:for\s*)?(\d+(?:\.\d{1,2})?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _is_total_offer(message: str, quantity: int) -> bool:
    if quantity <= 1:
        return False
    normalized = _normalize(message)
    total_markers = {
        "total",
        "altogether",
        "for both",
        "for all",
        "overall",
        "for 2",
        "for 3",
        "for 4",
        "for 5",
    }
    if any(marker in normalized for marker in total_markers):
        return True
    if "each" in normalized or "per copy" in normalized or "per book" in normalized:
        return False
    offered_amount = _extract_price_offer_amount(message)
    return offered_amount is not None and offered_amount > float(quantity)


def _is_negotiation_request(message: str) -> bool:
    normalized = _normalize(message)
    return any(keyword in normalized for keyword in NEGOTIATION_KEYWORDS) or _extract_price_offer_amount(message) is not None


def _is_global_negotiation_request(message: str) -> bool:
    normalized = _normalize(message)
    global_markers = ["all", "whole order", "entire order", "every book", "all books"]
    return any(marker in normalized for marker in global_markers)


def _is_review_query(message: str) -> bool:
    normalized = _normalize(message)
    if any(keyword in normalized for keyword in REVIEW_KEYWORDS):
        return True
    review_phrases = {
        "what do people think",
        "is it good",
        "is this book good",
        "how is this book",
        "worth reading",
        "reader feedback",
    }
    return any(phrase in normalized for phrase in review_phrases)


def _fetch_session(db: Session, session_id: str, user_id: int):
    return db.execute(
        text(
            """
            SELECT id, session_id, user_id, book_id, quantity, customer_name, phone, address, state
                 , negotiated_unit_price
            FROM assistant_conversations
            WHERE session_id = :session_id AND user_id = :user_id
            LIMIT 1
            """
        ),
        {"session_id": session_id, "user_id": user_id},
    ).mappings().first()


def _fetch_session_items(db: Session, session_id: str, user_id: int):
    return db.execute(
        text(
            """
            SELECT item.id, item.session_id, item.user_id, item.book_id, item.quantity, item.negotiated_unit_price,
                   book.title, book.author, book.price, book.stock_quantity
            FROM assistant_conversation_items item
            JOIN books book ON book.id = item.book_id
            WHERE item.session_id = :session_id AND item.user_id = :user_id
            ORDER BY item.id ASC
            """
        ),
        {"session_id": session_id, "user_id": user_id},
    ).mappings().all()


def _upsert_session(db: Session, session_id: str, user_id: int, **values) -> None:
    current = _fetch_session(db, session_id, user_id)

    if current:
        set_parts = []
        params = {"session_id": session_id, "user_id": user_id}
        for key, value in values.items():
            set_parts.append(f"{key} = :{key}")
            params[key] = value
        if set_parts:
            db.execute(
                text(
                    f"""
                    UPDATE assistant_conversations
                    SET {", ".join(set_parts)}
                    WHERE session_id = :session_id AND user_id = :user_id
                    """
                ),
                params,
            )
        return

    defaults = {
        "book_id": None,
        "quantity": None,
        "negotiated_unit_price": None,
        "customer_name": None,
        "phone": None,
        "address": None,
        "state": "idle",
    }
    defaults.update(values)
    db.execute(
        text(
            """
            INSERT INTO assistant_conversations (
                session_id, user_id, book_id, quantity, customer_name, phone, address, state
            )
            VALUES (
                :session_id, :user_id, :book_id, :quantity, :customer_name, :phone, :address, :state
            )
            """
        ),
        {"session_id": session_id, "user_id": user_id, **defaults},
    )


def _upsert_session_item(db: Session, session_id: str, user_id: int, book_id: int, **values) -> None:
    current = db.execute(
        text(
            """
            SELECT id
            FROM assistant_conversation_items
            WHERE session_id = :session_id AND user_id = :user_id AND book_id = :book_id
            LIMIT 1
            """
        ),
        {"session_id": session_id, "user_id": user_id, "book_id": book_id},
    ).first()

    if current:
        set_parts = []
        params = {"session_id": session_id, "user_id": user_id, "book_id": book_id}
        for key, value in values.items():
            set_parts.append(f"{key} = :{key}")
            params[key] = value
        if set_parts:
            db.execute(
                text(
                    f"""
                    UPDATE assistant_conversation_items
                    SET {", ".join(set_parts)}
                    WHERE session_id = :session_id AND user_id = :user_id AND book_id = :book_id
                    """
                ),
                params,
            )
        return

    defaults = {"quantity": None, "negotiated_unit_price": None}
    defaults.update(values)
    db.execute(
        text(
            """
            INSERT INTO assistant_conversation_items (
                session_id, user_id, book_id, quantity, negotiated_unit_price
            )
            VALUES (
                :session_id, :user_id, :book_id, :quantity, :negotiated_unit_price
            )
            """
        ),
        {"session_id": session_id, "user_id": user_id, "book_id": book_id, **defaults},
    )


def _reset_session(db: Session, session_id: str, user_id: int) -> None:
    db.execute(
        text(
            """
            DELETE FROM assistant_conversation_items
            WHERE session_id = :session_id AND user_id = :user_id
            """
        ),
        {"session_id": session_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            UPDATE assistant_conversations
            SET book_id = NULL,
                quantity = NULL,
                negotiated_unit_price = NULL,
                customer_name = NULL,
                phone = NULL,
                address = NULL,
                state = 'idle'
            WHERE session_id = :session_id AND user_id = :user_id
            """
        ),
        {"session_id": session_id, "user_id": user_id},
    )


def _get_book_by_id(db: Session, book_id: int | None) -> Book | None:
    if not book_id:
        return None
    return db.query(Book).filter(Book.id == book_id).first()


def _find_book_from_message(db: Session, message: str) -> Book | None:
    normalized = _normalize(message)
    books = db.query(Book).order_by(Book.title.asc()).all()

    exact_match = next((book for book in books if _normalize(book.title) == normalized), None)
    if exact_match:
        return exact_match

    title_match = next((book for book in books if _normalize(book.title) in normalized), None)
    if title_match:
        return title_match

    author_match = next((book for book in books if _normalize(book.author) in normalized), None)
    if author_match:
        return author_match

    search_terms = [part for part in re.split(r"[^a-zA-Z0-9]+", normalized) if len(part) >= 4]
    if not search_terms:
        return None

    query = db.query(Book)
    for term in search_terms[:4]:
        query = query.filter(or_(Book.title.ilike(f"%{term}%"), Book.author.ilike(f"%{term}%")))

    return query.order_by(Book.title.asc()).first()


def _find_category_from_message(message: str) -> str | None:
    normalized = _normalize(message)
    for alias, canonical in CATEGORY_ALIASES.items():
        if alias in normalized:
            return canonical
    return None


def _list_books_for_category(db: Session, category_name: str) -> list[Book]:
    return (
        db.query(Book)
        .join(Category, Category.id == Book.category_id)
        .filter(Category.name == category_name)
        .order_by(Book.title.asc())
        .limit(8)
        .all()
    )


def _build_order_summary(book: Book, quantity: int, name: str, phone: str, address: str) -> str:
    total = round(float(book.price) * quantity, 2)
    return (
        "ORDER SUMMARY:\n"
        f"Book: {book.title}\n"
        f"Quantity: {quantity}\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Address: {address}\n"
        f"Total: ${total:.2f}\n\n"
        "Please confirm by replying YES or CONFIRM to proceed."
    )


def _build_order_summary_with_price(book: Book, quantity: int, name: str, phone: str, address: str, unit_price: float) -> str:
    total = round(unit_price * quantity, 2)
    base_total = round(float(book.price) * quantity, 2)
    discount_amount = round(base_total - total, 2)
    return (
        "ORDER SUMMARY:\n"
        f"Book: {book.title}\n"
        f"Quantity: {quantity}\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Address: {address}\n"
        f"Original Total: ${base_total:.2f}\n"
        f"Discount: ${discount_amount:.2f}\n"
        f"Total: ${total:.2f}\n\n"
        "Please confirm by replying YES or CONFIRM to proceed."
    )


def _resolve_order_summary(book: Book, session, user: User) -> str:
    quantity = session["quantity"] or 1
    customer_name = session["customer_name"] or user.name
    phone = session["phone"] or "-"
    address = session["address"] or "-"
    negotiated_unit_price = float(session["negotiated_unit_price"]) if session and session["negotiated_unit_price"] is not None else None
    if negotiated_unit_price is not None:
        return _build_order_summary_with_price(book, quantity, customer_name, phone, address, negotiated_unit_price)
    return _build_order_summary(book, quantity, customer_name, phone, address)


def _build_multi_item_summary(items, session, user: User) -> str:
    customer_name = session["customer_name"] or user.name
    phone = session["phone"] or "-"
    address = session["address"] or "-"
    lines = ["ORDER SUMMARY:"]
    total_quantity = 0
    total_amount = 0.0

    for item in items:
        quantity = int(item["quantity"] or 0)
        if quantity <= 0:
            continue
        unit_price = float(item["negotiated_unit_price"]) if item["negotiated_unit_price"] is not None else float(item["price"])
        line_total = round(unit_price * quantity, 2)
        total_quantity += quantity
        total_amount += line_total
        lines.append(f"Book: {item['title']} x {quantity} - ${line_total:.2f}")

    lines.extend(
        [
            f"Quantity: {total_quantity}",
            f"Name: {customer_name}",
            f"Phone: {phone}",
            f"Address: {address}",
            f"Total: ${total_amount:.2f}",
            "",
            "Please confirm by replying YES or CONFIRM to proceed.",
        ]
    )
    return "\n".join(lines)


def _build_next_step_prompt(db: Session, session_id: str, book: Book, session, user: User) -> str:
    state = session["state"] if session else "idle"
    quantity = session["quantity"] or 1
    customer_name = session["customer_name"] or user.name

    if state == "book_selected":
        unit_price = float(session["negotiated_unit_price"]) if session and session["negotiated_unit_price"] is not None else float(book.price)
        return (
            f"\"{book.title}\" is ready at ${unit_price:.2f} per copy. "
            "Say 'place order' when you want me to collect your name, phone number, and address."
        )
    if state == "awaiting_quantity":
        return f"How many copies of \"{book.title}\" would you like to buy?"
    if state == "awaiting_name":
        return f"You'd like {quantity} copy{'ies' if quantity > 1 else ''} of \"{book.title}\". What is your full name?"
    if state == "awaiting_phone":
        return f"Thanks, {customer_name}. What phone number should we use for this order?"
    if state == "awaiting_address":
        return "Please share your full delivery address."
    if state == "awaiting_confirmation":
        return _render_order_summary(db, session_id, user, session, book)
    return f"How can I help you with \"{book.title}\"?"


def _render_order_summary(db: Session, session_id: str, user: User, session, current_book: Book) -> str:
    items = _fetch_session_items(db, session_id, user.id)
    completed_items = [item for item in items if int(item["quantity"] or 0) > 0]
    if len(completed_items) > 1:
        return _build_multi_item_summary(completed_items, session, user)
    return _resolve_order_summary(current_book, session, user)


def _build_negotiation_reply(book: Book, quantity: int, message: str):
    base_unit_price = float(book.price)
    minimum_unit_price = round(base_unit_price * (1 - MAX_NEGOTIATION_DISCOUNT), 2)
    requested_discount = _extract_discount_percent(message)
    offered_amount = _extract_price_offer_amount(message)
    is_total_offer = _is_total_offer(message, quantity)

    if requested_discount is not None:
        approved_discount = min(max(requested_discount, 0.03), MAX_NEGOTIATION_DISCOUNT)
        unit_price = round(base_unit_price * (1 - approved_discount), 2)
        total = round(unit_price * quantity, 2)
        return unit_price, (
            f"I can help with that. The best price I can offer is {int(approved_discount * 100)}% off for this order. "
            f"That brings \"{book.title}\" to ${unit_price:.2f} per copy and ${total:.2f} total for {quantity} cop"
            f"{'ies' if quantity > 1 else 'y'}. If you'd like, I can finalize the updated order summary now."
        )

    if offered_amount is not None:
        requested_unit_price = round(offered_amount / quantity, 2) if is_total_offer else round(offered_amount, 2)

        if requested_unit_price >= base_unit_price:
            total = round(base_unit_price * quantity, 2)
            return base_unit_price, (
                f"The current listed price is already better than that offer. \"{book.title}\" is ${base_unit_price:.2f} per copy, "
                f"so your total is ${total:.2f} for {quantity} cop{'ies' if quantity > 1 else 'y'}."
            )

        if requested_unit_price >= minimum_unit_price:
            unit_price = requested_unit_price
            total = round(unit_price * quantity, 2)
            offer_label = f"${offered_amount:.2f} total" if is_total_offer else f"${unit_price:.2f} per copy"
            return unit_price, (
                f"I can do {offer_label} for this order. That means \"{book.title}\" will be ${unit_price:.2f} per copy "
                f"and ${total:.2f} total for {quantity} cop{'ies' if quantity > 1 else 'y'}."
            )

        best_total = round(minimum_unit_price * quantity, 2)
        requested_label = f"${offered_amount:.2f} total" if is_total_offer else f"${requested_unit_price:.2f} per copy"
        return minimum_unit_price, (
            f"I can't go as low as {requested_label}. The best I can do is ${minimum_unit_price:.2f} per copy, "
            f"which is ${best_total:.2f} total for {quantity} cop{'ies' if quantity > 1 else 'y'}."
        )

    fallback_discount = 0.05
    unit_price = round(base_unit_price * (1 - fallback_discount), 2)
    total = round(unit_price * quantity, 2)
    return unit_price, (
        f"I can offer a better price on this order. I can do ${unit_price:.2f} per copy and ${total:.2f} total "
        f"for {quantity} cop{'ies' if quantity > 1 else 'y'}."
    )


def _build_review_summary(db: Session, book: Book) -> str:
    reviews = (
        db.query(Review)
        .join(User, User.id == Review.user_id)
        .filter(Review.book_id == book.id)
        .order_by(Review.created_at.desc())
        .limit(5)
        .all()
    )

    total_reviews = db.query(Review).filter(Review.book_id == book.id).count()
    average_rating = db.execute(
        text("SELECT AVG(rating) FROM reviews WHERE book_id = :book_id"),
        {"book_id": book.id},
    ).scalar()

    if not total_reviews:
        return (
            f"\"{book.title}\" does not have any customer reviews yet. "
            f"It is listed at ${float(book.price):.2f} and described as: {book.description or 'No description available.'}"
        )

    average_text = f"{float(average_rating):.1f}" if average_rating is not None else "0.0"
    response_lines = [
        f"Readers have rated \"{book.title}\" {average_text}/5 from {total_reviews} review{'s' if total_reviews != 1 else ''}.",
    ]

    commented_reviews = [review for review in reviews if review.comment and review.comment.strip()]
    if commented_reviews:
        response_lines.append("Here is what readers are saying:")
        for review in commented_reviews[:3]:
            reviewer_name = review.user.name if getattr(review, "user", None) else "A reader"
            trimmed_comment = review.comment.strip()
            if len(trimmed_comment) > 160:
                trimmed_comment = f"{trimmed_comment[:157].rstrip()}..."
            response_lines.append(f'- {reviewer_name} rated it {review.rating}/5: "{trimmed_comment}"')
    else:
        response_lines.append("The current ratings are positive, but no written comments have been left yet.")

    response_lines.append(
        f"If you want, I can also help you negotiate the price or start an order for \"{book.title}\"."
    )
    return "\n".join(response_lines)


def _handle_negotiation_anytime(db: Session, user: User, payload: AssistantChatRequest, session, current_book: Book):
    session_items = _fetch_session_items(db, payload.sessionId, user.id)
    if _is_global_negotiation_request(payload.chatInput):
        negotiated_parts = []
        for item in session_items:
            quantity = int(item["quantity"] or 0)
            if quantity <= 0:
                continue
            book = _get_book_by_id(db, item["book_id"])
            if not book:
                continue
            unit_price, _ = _build_negotiation_reply(book, quantity, payload.chatInput)
            _upsert_session_item(db, payload.sessionId, user.id, book.id, quantity=quantity, negotiated_unit_price=unit_price)
            negotiated_parts.append(f"{book.title} ${unit_price:.2f} per copy")

        if not negotiated_parts:
            db.commit()
            return {
                "reply": "I could not find any books in your current assistant order to negotiate. Please tell me which book you'd like to adjust.",
                "intent": "negotiation",
                "status": session["state"],
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }

        negotiation_reply = (
            f"Great! I’ve applied negotiation to your order items: {', '.join(negotiated_parts)}. "
            "You can continue adding books or confirm your order."
        )
        # for multi-item negotiation, keep session-level negotiated_unit_price for the latest selected book
        if current_book:
            current_item = next((item for item in session_items if item["book_id"] == current_book.id), None)
            if current_item and int(current_item["quantity"] or 0) > 0:
                unit_price, _ = _build_negotiation_reply(current_book, int(current_item["quantity"] or 1), payload.chatInput)
                _upsert_session(db, payload.sessionId, user.id, negotiated_unit_price=unit_price)

    else:
        if not current_book:
            db.commit()
            return {
                "reply": "Please tell me the book you want to negotiate, then I can offer the best price.",
                "intent": "negotiation",
                "status": session["state"],
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }

        effective_quantity = session["quantity"] or 1
        unit_price, negotiation_reply = _build_negotiation_reply(current_book, effective_quantity, payload.chatInput)
        _upsert_session(db, payload.sessionId, user.id, negotiated_unit_price=unit_price)
        _upsert_session_item(db, payload.sessionId, user.id, current_book.id, negotiated_unit_price=unit_price)

    refreshed_session = _fetch_session(db, payload.sessionId, user.id)
    follow_up = _build_next_step_prompt(db, payload.sessionId, current_book, refreshed_session, user)
    reply = f"{negotiation_reply}\n\n{follow_up}" if not _is_global_negotiation_request(payload.chatInput) else f"{negotiation_reply}\n\n{follow_up}"

    db.commit()
    return {
        "reply": reply,
        "intent": "negotiation",
        "status": refreshed_session["state"],
        "sessionId": payload.sessionId,
        "timestamp": _now_iso(),
    }


def send_message_to_assistant(db: Session, user: User, payload: AssistantChatRequest):
    message = payload.chatInput.strip()
    normalized = _normalize(message)
    session = _fetch_session(db, payload.sessionId, user.id)
    state = session["state"] if session else "idle"
    current_book = _get_book_by_id(db, session["book_id"] if session else None)
    detected_book = _find_book_from_message(db, message)

    if not session:
        _upsert_session(db, payload.sessionId, user.id)
        session = _fetch_session(db, payload.sessionId, user.id)
        state = "idle"

    if not message or _is_greeting(message):
        webhook_reply, token_usage = _try_n8n_assistant_reply(
            user,
            payload,
            state=state,
            current_book=current_book,
            intent_hint="general",
        )
        if webhook_reply:
            db.commit()
            return {
                "reply": webhook_reply,
                "intent": "general",
                "status": "active",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
                "tokenUsage": token_usage,
            }
        db.commit()
        return {
            "reply": (
                "Hello! I'm your bookstore assistant. Ask for a book, author, price, recommendation, "
                "or tell me what you'd like to order."
            ),
            "intent": "general",
            "status": "active",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if _is_cancellation(message):
        _reset_session(db, payload.sessionId, user.id)
        db.commit()
        return {
            "reply": "Your current assistant order draft has been cancelled. Ask for any book whenever you're ready.",
            "intent": "cancel",
            "status": "cancelled",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if _is_negotiation_request(message):
        # Allow negotiation at any time, even when current book is not selected in state.
        if not current_book:
            candidates = _fetch_session_items(db, payload.sessionId, user.id)
            last_book_item = next((item for item in reversed(candidates) if int(item["quantity"] or 0) > 0), None)
            if last_book_item:
                current_book = _get_book_by_id(db, last_book_item["book_id"])

        if current_book or _is_global_negotiation_request(message):
            return _handle_negotiation_anytime(db, user, payload, session, current_book)

    if _is_review_query(message):
        review_book = detected_book or current_book
        if not review_book:
            db.commit()
            return {
                "reply": "Tell me the title of the book you want reviews for, and I will summarize the reader feedback for you.",
                "intent": "reviews",
                "status": state,
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }

        webhook_reply, token_usage = _try_n8n_assistant_reply(
            user,
            payload,
            state=state,
            current_book=review_book,
            intent_hint="reviews",
        )
        if webhook_reply:
            db.commit()
            return {
                "reply": webhook_reply,
                "intent": "reviews",
                "status": state,
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
                "tokenUsage": token_usage,
            }

        db.commit()
        return {
            "reply": _build_review_summary(db, review_book),
            "intent": "reviews",
            "status": state,
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "book_selected" and current_book and _is_place_order_request(message):
        quantity = _extract_quantity(message) or session["quantity"] or 1
        unit_price = float(session["negotiated_unit_price"]) if session and session["negotiated_unit_price"] is not None else float(current_book.price)
        if quantity <= 0:
            quantity = 1
        if quantity > current_book.stock_quantity:
            db.commit()
            return {
                "reply": (
                    f"We currently have {current_book.stock_quantity} copies of \"{current_book.title}\" in stock. "
                    "Please choose a lower quantity."
                ),
                "intent": "order",
                "status": "stock_limit",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }
        _upsert_session(db, payload.sessionId, user.id, quantity=quantity, state="awaiting_name")
        _upsert_session_item(db, payload.sessionId, user.id, current_book.id, quantity=quantity)
        db.commit()
        return {
            "reply": (
                f"You selected \"{current_book.title}\" for ${unit_price:.2f} per copy"
                f"{' and ' + str(quantity) + ' copies' if quantity > 1 else ''}. "
                "What is your full name?"
            ),
            "intent": "order",
            "status": "collecting_name",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if detected_book and (current_book is None or detected_book.id != current_book.id):
        _upsert_session(db, payload.sessionId, user.id, book_id=detected_book.id, quantity=None, negotiated_unit_price=None, state="book_selected")
        _upsert_session_item(db, payload.sessionId, user.id, detected_book.id)
        db.commit()
        existing_items = [item for item in _fetch_session_items(db, payload.sessionId, user.id) if item["book_id"] != detected_book.id and int(item["quantity"] or 0) > 0]
        existing_note = ""
        if existing_items:
            existing_note = f" I already kept {len(existing_items)} other book{'s' if len(existing_items) > 1 else ''} in this order."
        return {
            "reply": (
                f"You selected \"{detected_book.title}\" by {detected_book.author}.{existing_note} "
                f"The price is ${float(detected_book.price):.2f} per copy. "
                "You can ask for reviews, negotiate the price, or say 'place order' when you want me to collect your details."
            ),
            "intent": "book_selected",
            "status": "book_selected",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if "list" in normalized or "recommend" in normalized:
        webhook_reply, token_usage = _try_n8n_assistant_reply(
            user,
            payload,
            state=state,
            current_book=current_book,
            intent_hint="browse",
        )
        if webhook_reply:
            db.commit()
            return {
                "reply": webhook_reply,
                "intent": "browse",
                "status": "active",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
                "tokenUsage": token_usage,
            }

        category_name = _find_category_from_message(message)
        if category_name:
            books = _list_books_for_category(db, category_name)
            if books:
                listing = "\n".join(
                    f"{index}. \"{book.title}\" by {book.author} - ${float(book.price):.2f}"
                    for index, book in enumerate(books, start=1)
                )
                db.commit()
                return {
                    "reply": (
                        f"Here are some {category_name.lower()} books we have:\n\n{listing}\n\n"
                        "Tell me the book title you want and I will help you place the order."
                    ),
                    "intent": "browse",
                    "status": "active",
                    "sessionId": payload.sessionId,
                    "timestamp": _now_iso(),
                }

        books = db.query(Book).order_by(Book.title.asc()).limit(8).all()
        listing = "\n".join(
            f"- \"{book.title}\" by {book.author} - ${float(book.price):.2f}" for book in books
        )
        db.commit()
        return {
            "reply": (
                f"Here are some books currently available:\n\n{listing}\n\n"
                "Tell me which title you want and I will guide the full order."
            ),
            "intent": "browse",
            "status": "active",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "awaiting_quantity" and current_book:
        quantity = _extract_quantity(message)
        if quantity is None or quantity <= 0:
            db.commit()
            return {
                "reply": f"How many copies of \"{current_book.title}\" would you like to buy?",
                "intent": "order",
                "status": "collecting_quantity",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }
        if quantity > current_book.stock_quantity:
            db.commit()
            return {
                "reply": (
                    f"We currently have {current_book.stock_quantity} copies of \"{current_book.title}\" in stock. "
                    "Please choose a lower quantity."
                ),
                "intent": "order",
                "status": "stock_limit",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }
        _upsert_session(db, payload.sessionId, user.id, quantity=quantity, state="awaiting_name")
        _upsert_session_item(db, payload.sessionId, user.id, current_book.id, quantity=quantity)
        db.commit()
        return {
            "reply": f"You'd like {quantity} copy{'ies' if quantity > 1 else ''} of \"{current_book.title}\". What is your full name?",
            "intent": "order",
            "status": "collecting_name",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "awaiting_name" and current_book:
        name = message.strip()
        _upsert_session(db, payload.sessionId, user.id, customer_name=name, state="awaiting_phone")
        db.commit()
        return {
            "reply": f"Thanks, {name}. What phone number should we use for this order?",
            "intent": "order",
            "status": "collecting_phone",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "awaiting_phone" and current_book:
        phone = _extract_phone(message) or message.strip()
        _upsert_session(db, payload.sessionId, user.id, phone=phone, state="awaiting_address")
        db.commit()
        return {
            "reply": "Please share your full delivery address.",
            "intent": "order",
            "status": "collecting_address",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "awaiting_address" and current_book:
        address = message.strip()
        _upsert_session(db, payload.sessionId, user.id, address=address, state="awaiting_confirmation")
        session = _fetch_session(db, payload.sessionId, user.id)
        db.commit()
        return {
            "reply": _render_order_summary(db, payload.sessionId, user, session, current_book),
            "intent": "order",
            "status": "awaiting_confirmation",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    if state == "awaiting_confirmation" and current_book:
        if _is_confirmation(message):
            order_payload = AssistantOrderCreate(
                sessionId=payload.sessionId,
                book=current_book.title if current_book else None,
                quantity=session["quantity"] if session and session.get("quantity") else None,
                name=session["customer_name"] if session and session.get("customer_name") else user.name,
                phone=session["phone"] if session and session.get("phone") else None,
                address=session["address"] if session and session.get("address") else None,
            )
            order_result = place_assistant_order(db, user, order_payload)
            db.commit()
            return {
                "reply": (
                    f"Order confirmed and placed successfully as Order #{order_result['order_id']} for "
                    f"{order_result['quantity']} item{'s' if order_result['quantity'] != 1 else ''}. "
                    f"Total amount: ${order_result['total']:.2f}."
                ),
                "intent": "order",
                "status": "confirmed",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }

        db.commit()
        return {
            "reply": _render_order_summary(db, payload.sessionId, user, session, current_book),
            "intent": "order",
            "status": "awaiting_confirmation",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    book = detected_book
    if book:
        _upsert_session(db, payload.sessionId, user.id, book_id=book.id, quantity=None, negotiated_unit_price=None, customer_name=None, phone=None, address=None, state="book_selected")
        _upsert_session_item(db, payload.sessionId, user.id, book.id)
        db.commit()
        return {
            "reply": (
                f"\"{book.title}\" by {book.author} is available for ${float(book.price):.2f}. "
                f"We currently have {book.stock_quantity} copies in stock. "
                "You can ask for reviews, negotiate, or say 'place order' when you want me to collect your name, phone number, and address."
            ),
            "intent": "book_selected",
            "status": "book_selected",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
        }

    category_name = _find_category_from_message(message)
    if category_name:
        books = _list_books_for_category(db, category_name)
        if books:
            listing = "\n".join(
                f"- \"{book.title}\" by {book.author} - ${float(book.price):.2f}" for book in books
            )
            db.commit()
            return {
                "reply": (
                    f"We have these {category_name.lower()} books:\n\n{listing}\n\n"
                    "Tell me the exact title you want to order."
                ),
                "intent": "browse",
                "status": "active",
                "sessionId": payload.sessionId,
                "timestamp": _now_iso(),
            }

    db.commit()
    webhook_reply, token_usage = _try_n8n_assistant_reply(
        user,
        payload,
        state=state,
        current_book=current_book,
        intent_hint="general",
    )
    if webhook_reply:
        return {
            "reply": webhook_reply,
            "intent": "general",
            "status": "active",
            "sessionId": payload.sessionId,
            "timestamp": _now_iso(),
            "tokenUsage": token_usage,
        }

    return {
        "reply": (
            "I can help you find a book and place the order. Tell me a book title, an author, or a category like "
            "fiction, non fiction, self improvement, or business."
        ),
        "intent": "general",
        "status": "active",
        "sessionId": payload.sessionId,
        "timestamp": _now_iso(),
    }


def place_assistant_order(db: Session, user: User, payload: AssistantOrderCreate):
    existing_row = db.execute(
        text(
            """
            SELECT order_id
            FROM assistant_order_sessions
            WHERE session_id = :session_id AND user_id = :user_id
            LIMIT 1
            """
        ),
        {"session_id": payload.sessionId, "user_id": user.id},
    ).first()

    if existing_row:
        existing_order = db.query(Order).filter(Order.id == existing_row.order_id).first()
        existing_item = (
            db.query(OrderItem)
            .filter(OrderItem.order_id == existing_row.order_id)
            .order_by(OrderItem.id.asc())
            .first()
        )
        book_title = payload.book
        quantity = payload.quantity
        if existing_item:
            existing_book = db.query(Book).filter(Book.id == existing_item.book_id).first()
            book_title = existing_book.title if existing_book else book_title
            quantity = existing_item.quantity
        return {
            "order_id": existing_row.order_id,
            "book": book_title,
            "quantity": quantity,
            "total": float(existing_order.total_amount) if existing_order else 0,
            "status": existing_order.status if existing_order else "pending",
        }

    session = _fetch_session(db, payload.sessionId, user.id)
    session_items = [item for item in _fetch_session_items(db, payload.sessionId, user.id) if int(item["quantity"] or 0) > 0]
    session_book = _get_book_by_id(db, session["book_id"] if session else None)

    if not session_items:
        book = session_book
        if not book and payload.book:
            normalized_title = payload.book.strip()
            book = (
                db.query(Book)
                .filter(Book.title.ilike(normalized_title))
                .order_by(Book.id.asc())
                .first()
            )

        if not book:
            raise AppException(404, "Book not found for assistant order")

        quantity = payload.quantity or 0
        if session and session["quantity"]:
            quantity = session["quantity"]

        if quantity <= 0:
            raise AppException(400, "Quantity must be greater than zero")

        if book.stock_quantity < quantity:
            raise AppException(400, f"Insufficient stock for {book.title}")

        session_items = [
            {
                "book_id": book.id,
                "title": book.title,
                "price": float(book.price),
                "stock_quantity": int(book.stock_quantity),
                "quantity": quantity,
                "negotiated_unit_price": float(session["negotiated_unit_price"]) if session and session["negotiated_unit_price"] is not None else None,
            }
        ]

    for item in session_items:
        if int(item["quantity"]) <= 0:
            raise AppException(400, "Quantity must be greater than zero for every selected book")
        if int(item["stock_quantity"]) < int(item["quantity"]):
            raise AppException(400, f"Insufficient stock for {item['title']}")

    total = round(
        sum(
            (float(item["negotiated_unit_price"]) if item["negotiated_unit_price"] is not None else float(item["price"]))
            * int(item["quantity"])
            for item in session_items
        ),
        2,
    )
    order = Order(user_id=user.id, total_amount=total, status="pending")
    db.add(order)
    db.flush()

    primary_book_title = None
    total_quantity = 0
    for item in session_items:
        db.add(
            OrderItem(
                order_id=order.id,
                book_id=int(item["book_id"]),
                quantity=int(item["quantity"]),
                price_at_purchase=(
                    float(item["negotiated_unit_price"]) if item["negotiated_unit_price"] is not None else float(item["price"])
                ),
            )
        )
        book_record = db.query(Book).filter(Book.id == int(item["book_id"])).first()
        if book_record:
            book_record.stock_quantity -= int(item["quantity"])
            if primary_book_title is None:
                primary_book_title = book_record.title
        total_quantity += int(item["quantity"])

    db.execute(
        text(
            """
            INSERT INTO assistant_order_sessions (session_id, user_id, order_id)
            VALUES (:session_id, :user_id, :order_id)
            """
        ),
        {"session_id": payload.sessionId, "user_id": user.id, "order_id": order.id},
    )
    _reset_session(db, payload.sessionId, user.id)
    db.commit()

    return {
        "order_id": order.id,
        "book": primary_book_title or (payload.book or "Book order"),
        "quantity": total_quantity,
        "total": total,
        "status": order.status,
    }
