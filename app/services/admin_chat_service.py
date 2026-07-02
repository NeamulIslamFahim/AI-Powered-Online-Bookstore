"""
Admin chatbot service — handles navigation AND book CRUD via conversational flow.

Conversation state is kept in-memory per admin session using a simple dict keyed
by a session_id sent from the frontend.  State machine:

  idle
    → add_book:     collect title, author, price, stock, category_id, description, image_url
    → delete_book:  ask for book id, confirm, then call delete
    → edit_book:    ask for book id, then field/value pairs, then confirm
"""

import re
from typing import Optional
from app.db.session import SessionLocal
from app.services.book_service import create_book, delete_book, get_book_by_id, update_book
from app.schemas.book import BookCreate, BookUpdate

# ── In-memory conversation state per session ──────────────────────────────────
# { session_id: { "state": str, "data": dict } }
_sessions: dict[str, dict] = {}

REQUIRED_ADD_FIELDS = ["title", "author", "price", "stock_quantity", "category_id"]
ADD_FIELD_PROMPTS = {
    "title": "What is the book title?",
    "author": "Who is the author?",
    "price": "What is the price? (e.g. 14.99)",
    "stock_quantity": "How many copies are in stock?",
    "category_id": "What is the category ID? (1=Fiction, 2=Non-Fiction, 3=Self Improvement, 4=Business)",
    "description": "Enter a short description (or type 'skip' to leave it blank).",
    "image_url": "Paste an image URL (or type 'skip' to leave it blank).",
}
ALL_ADD_FIELDS = list(ADD_FIELD_PROMPTS.keys())


def _session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"state": "idle", "data": {}}
    return _sessions[session_id]


def _reset(session_id: str) -> None:
    _sessions[session_id] = {"state": "idle", "data": {}}


def _reply(action: str, target: Optional[str], text: str) -> dict:
    return {"action": action, "target": target, "reply": text}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(msg: str) -> str:
    return re.sub(r"\s+", " ", msg.strip().lower())


def _is_cancel(msg: str) -> bool:
    return _normalize(msg) in {"cancel", "stop", "quit", "exit", "abort", "no"}


def _next_missing_field(data: dict, fields: list) -> Optional[str]:
    for f in fields:
        if f not in data:
            return f
    return None


# ── Intent detection (idle state) ─────────────────────────────────────────────

def _detect_intent(normalized: str) -> Optional[str]:
    if any(k in normalized for k in ["add book", "add a book", "create book", "new book"]):
        return "add_book_start"
    if any(k in normalized for k in ["delete book", "remove book", "delete a book"]):
        return "delete_book_start"
    if any(k in normalized for k in ["edit book", "update book", "modify book", "change book"]):
        return "edit_book_start"
    if any(k in normalized for k in ["users", "manage users", "user management", "customers"]):
        return "nav_users"
    if any(k in normalized for k in ["sessions", "active sessions", "user sessions"]):
        return "nav_sessions"
    if any(k in normalized for k in ["books", "products", "inventory", "manage books", "book list"]):
        return "nav_books"
    if any(k in normalized for k in ["dashboard", "analytics", "stats", "statistics", "home", "orders"]):
        return "nav_dashboard"
    return None


# ── ADD BOOK flow ─────────────────────────────────────────────────────────────

def _handle_add_book(session_id: str, message: str) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if state == "idle":
        # Just entered the flow
        sess["state"] = "add_book"
        return _reply("NONE", None, "Let's add a new book! 📚\n" + ADD_FIELD_PROMPTS["title"])

    if state == "add_book":
        if _is_cancel(message):
            _reset(session_id)
            return _reply("NONE", None, "Book creation cancelled.")

        # Figure out which field we're collecting
        missing = _next_missing_field(data, ALL_ADD_FIELDS)
        if missing is None:
            # All fields collected — create
            return _do_create_book(session_id, data)

        raw = message.strip()

        # Skip optional fields
        if raw.lower() in {"skip", "none", "-"} and missing not in REQUIRED_ADD_FIELDS:
            data[missing] = None
        else:
            # Type-cast
            try:
                if missing == "price":
                    data[missing] = float(raw)
                elif missing in ("stock_quantity", "category_id"):
                    data[missing] = int(raw)
                else:
                    data[missing] = raw
            except ValueError:
                return _reply("NONE", None, f"That doesn't look right. {ADD_FIELD_PROMPTS[missing]}")

        # Ask next field
        next_field = _next_missing_field(data, ALL_ADD_FIELDS)
        if next_field is None:
            return _do_create_book(session_id, data)
        return _reply("NONE", None, ADD_FIELD_PROMPTS[next_field])

    return _reply("NONE", None, "Unexpected state. Type 'cancel' to restart.")


def _do_create_book(session_id: str, data: dict) -> dict:
    try:
        db = SessionLocal()
        payload = BookCreate(
            title=data["title"],
            author=data["author"],
            price=data["price"],
            stock_quantity=data["stock_quantity"],
            category_id=data["category_id"],
            description=data.get("description"),
            image_url=data.get("image_url"),
            isbn=data.get("isbn"),
            published_date=None,
        )
        book = create_book(db, payload)
        db.close()
        _reset(session_id)
        return _reply(
            "NAVIGATE",
            "/admin/books",
            f"✅ Book **\"{book.title}\"** added successfully (ID: {book.id})! Navigating to Book Management.",
        )
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to create book: {exc}")


# ── DELETE BOOK flow ──────────────────────────────────────────────────────────

def _handle_delete_book(session_id: str, message: str) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if _is_cancel(message):
        _reset(session_id)
        return _reply("NONE", None, "Delete cancelled.")

    if state == "idle":
        sess["state"] = "delete_book_ask_id"
        return _reply("NONE", None, "Which book do you want to delete? Please provide the **Book ID**.")

    if state == "delete_book_ask_id":
        try:
            book_id = int(message.strip())
        except ValueError:
            return _reply("NONE", None, "Please enter a valid numeric Book ID.")
        try:
            db = SessionLocal()
            book = get_book_by_id(db, book_id)
            db.close()
        except Exception:
            return _reply("NONE", None, f"No book found with ID {book_id}. Please try again or type 'cancel'.")
        data["book_id"] = book_id
        data["book_title"] = book.title
        sess["state"] = "delete_book_confirm"
        return _reply(
            "NONE", None,
            f"⚠️ Are you sure you want to permanently delete **\"{book.title}\"** (ID: {book_id})?\n"
            "Type **yes** to confirm or **cancel** to abort."
        )

    if state == "delete_book_confirm":
        if message.strip().lower() in {"yes", "y", "confirm", "delete"}:
            try:
                db = SessionLocal()
                delete_book(db, data["book_id"])
                db.close()
                title = data.get("book_title", "the book")
                _reset(session_id)
                return _reply("NAVIGATE", "/admin/books", f"✅ **\"{title}\"** has been deleted successfully.")
            except Exception as exc:
                _reset(session_id)
                return _reply("NONE", None, f"❌ Failed to delete: {exc}")
        _reset(session_id)
        return _reply("NONE", None, "Delete cancelled.")

    return _reply("NONE", None, "Unexpected state. Type 'cancel' to restart.")


# ── EDIT BOOK flow ────────────────────────────────────────────────────────────

EDITABLE_FIELDS = {
    "title": str, "author": str, "description": str, "price": float,
    "stock_quantity": int, "category_id": int, "image_url": str, "isbn": str,
}


def _handle_edit_book(session_id: str, message: str) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if _is_cancel(message):
        _reset(session_id)
        return _reply("NONE", None, "Edit cancelled.")

    if state == "idle":
        sess["state"] = "edit_book_ask_id"
        return _reply("NONE", None, "Which book do you want to edit? Please provide the **Book ID**.")

    if state == "edit_book_ask_id":
        try:
            book_id = int(message.strip())
        except ValueError:
            return _reply("NONE", None, "Please enter a valid numeric Book ID.")
        try:
            db = SessionLocal()
            book = get_book_by_id(db, book_id)
            db.close()
        except Exception:
            return _reply("NONE", None, f"No book found with ID {book_id}. Try again or type 'cancel'.")
        data["book_id"] = book_id
        data["current"] = {
            "title": book.title, "author": book.author, "description": book.description,
            "price": book.price, "stock_quantity": book.stock_quantity,
            "category_id": book.category_id, "image_url": book.image_url, "isbn": book.isbn,
        }
        sess["state"] = "edit_book_ask_field"
        fields_str = ", ".join(EDITABLE_FIELDS.keys())
        return _reply(
            "NONE", None,
            f"Editing **\"{book.title}\"** (ID: {book_id}).\n"
            f"Which field do you want to change? Options: {fields_str}\n"
            f"Or type **done** to save, **cancel** to abort."
        )

    if state == "edit_book_ask_field":
        stripped = message.strip().lower()
        if stripped == "done":
            return _do_update_book(session_id, data)
        if stripped not in EDITABLE_FIELDS:
            return _reply("NONE", None, f"Unknown field '{stripped}'. Choose from: {', '.join(EDITABLE_FIELDS.keys())} or type 'done'.")
        data["editing_field"] = stripped
        sess["state"] = "edit_book_ask_value"
        current_val = data["current"].get(stripped, "N/A")
        return _reply("NONE", None, f"Current **{stripped}**: `{current_val}`\nEnter new value:")

    if state == "edit_book_ask_value":
        field = data.get("editing_field")
        raw = message.strip()
        try:
            cast = EDITABLE_FIELDS[field]
            data["current"][field] = cast(raw)
        except (ValueError, KeyError):
            return _reply("NONE", None, f"Invalid value for {field}. Please try again.")
        sess["state"] = "edit_book_ask_field"
        fields_str = ", ".join(EDITABLE_FIELDS.keys())
        return _reply(
            "NONE", None,
            f"✔ **{field}** updated to `{raw}`.\n"
            f"Change another field or type **done** to save."
        )

    return _reply("NONE", None, "Unexpected state. Type 'cancel' to restart.")


def _do_update_book(session_id: str, data: dict) -> dict:
    try:
        db = SessionLocal()
        current = data["current"]
        payload = BookUpdate(
            title=current["title"],
            author=current["author"],
            price=float(current["price"]),
            stock_quantity=int(current["stock_quantity"]),
            category_id=int(current["category_id"]) if current.get("category_id") else 1,
            description=current.get("description"),
            image_url=current.get("image_url"),
            isbn=current.get("isbn"),
            published_date=None,
        )
        book = update_book(db, data["book_id"], payload)
        db.close()
        _reset(session_id)
        return _reply("NAVIGATE", "/admin/books", f"✅ **\"{book.title}\"** updated successfully!")
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to update book: {exc}")


# ── Main entry point ──────────────────────────────────────────────────────────

def process_admin_command(message: str, session_id: str = "default") -> dict:
    sess = _session(session_id)
    state = sess["state"]
    normalized = _normalize(message)

    # Allow cancel from any state
    if _is_cancel(message) and state != "idle":
        _reset(session_id)
        return _reply("NONE", None, "Operation cancelled. How can I help you?")

    # Route active flows
    if state.startswith("add_book"):
        return _handle_add_book(session_id, message)
    if state.startswith("delete_book"):
        return _handle_delete_book(session_id, message)
    if state.startswith("edit_book"):
        return _handle_edit_book(session_id, message)

    # Idle — detect intent
    intent = _detect_intent(normalized)

    if intent == "add_book_start":
        return _handle_add_book(session_id, message)
    if intent == "delete_book_start":
        return _handle_delete_book(session_id, message)
    if intent == "edit_book_start":
        return _handle_edit_book(session_id, message)
    if intent == "nav_users":
        return _reply("NAVIGATE", "/admin/users", "Navigating to User Management...")
    if intent == "nav_sessions":
        return _reply("NAVIGATE", "/admin/sessions", "Navigating to Session Management...")
    if intent == "nav_books":
        return _reply("NAVIGATE", "/admin/books", "Navigating to Book Management...")
    if intent == "nav_dashboard":
        return _reply("NAVIGATE", "/admin", "Navigating to the Admin Dashboard...")

    return _reply(
        "NONE", None,
        "I can help you:\n"
        "• **Navigate**: 'go to users', 'manage books', 'show sessions'\n"
        "• **Add a book**: 'add book'\n"
        "• **Edit a book**: 'edit book'\n"
        "• **Delete a book**: 'delete book'"
    )
