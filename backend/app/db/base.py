from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.book import Book  # noqa: E402,F401
from app.models.cart import Cart, CartItem  # noqa: E402,F401
from app.models.category import Category  # noqa: E402,F401
from app.models.order import Order, OrderItem  # noqa: E402,F401
from app.models.review import Review  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.wishlist import Wishlist  # noqa: E402,F401
