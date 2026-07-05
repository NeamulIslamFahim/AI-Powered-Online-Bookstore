from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.cart import Cart, CartItem
from app.models.user import User


def _serialize_cart(cart: Cart):
    subtotal = 0
    items = []
    for item in cart.items:
      line_total = float(item.book.price) * item.quantity
      subtotal += line_total
      item.subtotal = round(line_total, 2)
      items.append(item)
    cart.items = items
    cart.subtotal = round(subtotal, 2)
    return cart


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.book).joinedload(Book.category))
        .filter(Cart.user_id == user.id)
        .first()
    )
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        cart = (
            db.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.book).joinedload(Book.category))
            .filter(Cart.user_id == user.id)
            .first()
        )
    return _serialize_cart(cart)


def add_item_to_cart(db: Session, user: User, *, book_id: int, quantity: int):
    cart = get_or_create_cart(db, user)
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise AppException(404, "Book not found")

    existing_item = next((item for item in cart.items if item.book_id == book_id), None)
    new_quantity = quantity if not existing_item else existing_item.quantity + quantity
    if new_quantity > book.stock_quantity:
        raise AppException(400, "Requested quantity exceeds stock")

    if existing_item:
        existing_item.quantity = new_quantity
    else:
        db.add(CartItem(cart_id=cart.id, book_id=book_id, quantity=quantity))

    db.commit()
    return get_or_create_cart(db, user)


def update_cart_item(db: Session, user: User, *, book_id: int, quantity: int):
    cart = get_or_create_cart(db, user)
    item = next((entry for entry in cart.items if entry.book_id == book_id), None)
    if not item:
        raise AppException(404, "Cart item not found")
    if quantity > item.book.stock_quantity:
        raise AppException(400, "Requested quantity exceeds stock")
    item.quantity = quantity
    db.commit()
    return get_or_create_cart(db, user)


def remove_cart_item(db: Session, user: User, *, book_id: int):
    cart = get_or_create_cart(db, user)
    item = next((entry for entry in cart.items if entry.book_id == book_id), None)
    if not item:
        raise AppException(404, "Cart item not found")
    db.delete(item)
    db.commit()
    return get_or_create_cart(db, user)


def clear_cart_items(db: Session, user: User):
    cart = get_or_create_cart(db, user)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    return get_or_create_cart(db, user)
