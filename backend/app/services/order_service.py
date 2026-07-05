from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.book import Book
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.user import User

STATUS_FLOW = ["pending", "paid", "shipped", "delivered"]
ACTIVE_ORDER_STATUSES = ["pending", "paid", "shipped"]


def checkout(db: Session, user: User):
    # Load the user's cart and all referenced books up front so stock validation
    # and order creation happen against a single consistent unit of work.
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.book))
        .filter(Cart.user_id == user.id)
        .first()
    )
    if not cart or not cart.items:
        raise AppException(400, "Cart is empty")

    total = 0.0
    for item in cart.items:
        if item.quantity > item.book.stock_quantity:
            raise AppException(400, f"Insufficient stock for {item.book.title}")
        total += float(item.book.price) * item.quantity

    order = Order(user_id=user.id, total_amount=round(total, 2), status="pending")
    db.add(order)
    db.flush()

    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                book_id=item.book_id,
                quantity=item.quantity,
                price_at_purchase=float(item.book.price),
            )
        )
        item.book.stock_quantity -= item.quantity
        db.delete(item)

    db.commit()
    db.refresh(order)
    return get_order_by_id(db, order.id, user.id, is_admin=True)


def get_orders_for_user(db: Session, user: User):
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.book).joinedload(Book.category))
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


def get_order_by_id(db: Session, order_id: int, user_id: int | None = None, *, is_admin: bool = False):
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.book).joinedload(Book.category),
        joinedload(Order.user),
    )
    if not is_admin:
        query = query.filter(Order.user_id == user_id)
    order = query.filter(Order.id == order_id).first()
    if not order:
        raise AppException(404, "Order not found")
    return order


def get_all_orders(db: Session):
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.book).joinedload(Book.category), joinedload(Order.user))
        .order_by(Order.created_at.desc())
        .all()
    )


def update_order_status(db: Session, order_id: int, status: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise AppException(404, "Order not found")

    if order.status == "cancelled":
        raise AppException(400, "Cancelled orders cannot be updated")
    if order.status == "delivered":
        raise AppException(400, "Delivered orders cannot be updated")

    if status == "cancelled":
        if order.status not in ACTIVE_ORDER_STATUSES:
            raise AppException(400, "Only active orders can be cancelled")
        order.status = status
    else:
        current_index = STATUS_FLOW.index(order.status)
        next_index = STATUS_FLOW.index(status)
        if next_index < current_index:
            raise AppException(400, "Order status cannot move backward")
        order.status = status

    db.commit()
    return get_order_by_id(db, order.id, is_admin=True, user_id=None)


def get_admin_stats(db: Session, start_date: date | None = None, end_date: date | None = None):
    low_stock_books = db.query(Book).options(joinedload(Book.category)).filter(Book.stock_quantity <= settings.LOW_STOCK_THRESHOLD).all()
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    range_end_date = end_date or now.date()
    range_start_date = start_date or (range_end_date - timedelta(days=6))

    if range_start_date > range_end_date:
        raise AppException(400, "Start date cannot be after end date")

    range_start = datetime.combine(range_start_date, time.min)
    range_end = datetime.combine(range_end_date + timedelta(days=1), time.min)

    active_orders = db.query(Order).filter(Order.status != "cancelled")
    revenue = active_orders.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).scalar() or 0
    total_units_sold = (
        db.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.status != "cancelled")
        .scalar()
        or 0
    )
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    average_order_value = float(revenue) / total_orders if total_orders else 0

    revenue_today = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status != "cancelled", Order.created_at >= day_start)
        .scalar()
        or 0
    )
    revenue_month = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status != "cancelled", Order.created_at >= month_start)
        .scalar()
        or 0
    )
    revenue_year = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status != "cancelled", Order.created_at >= year_start)
        .scalar()
        or 0
    )

    orders_today = db.query(func.count(Order.id)).filter(Order.created_at >= day_start).scalar() or 0
    orders_month = db.query(func.count(Order.id)).filter(Order.created_at >= month_start).scalar() or 0
    orders_year = db.query(func.count(Order.id)).filter(Order.created_at >= year_start).scalar() or 0

    top_selling_rows = (
        db.query(
            Book.id,
            Book.title,
            Book.author,
            Book.stock_quantity,
            Book.price,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price_at_purchase), 0).label("revenue"),
        )
        .outerjoin(OrderItem, OrderItem.book_id == Book.id)
        .outerjoin(Order, OrderItem.order_id == Order.id)
        .filter((Order.id.is_(None)) | (Order.status != "cancelled"))
        .group_by(Book.id)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc(), Book.title.asc())
        .limit(6)
        .all()
    )

    category_rows = (
        db.query(
            Category.id,
            Category.name,
            func.count(Book.id).label("books_count"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price_at_purchase), 0).label("revenue"),
        )
        .outerjoin(Book, Book.category_id == Category.id)
        .outerjoin(OrderItem, OrderItem.book_id == Book.id)
        .outerjoin(Order, OrderItem.order_id == Order.id)
        .filter((Order.id.is_(None)) | (Order.status != "cancelled"))
        .group_by(Category.id)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc(), Category.name.asc())
        .all()
    )

    sales_timeline = []
    total_range_days = (range_end_date - range_start_date).days + 1
    for day_offset in range(total_range_days):
        start = datetime.combine(range_start_date + timedelta(days=day_offset), time.min)
        end = start + timedelta(days=1)
        point_revenue = (
            db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status != "cancelled", Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        point_orders = (
            db.query(func.count(Order.id))
            .filter(Order.status != "cancelled", Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        point_units = (
            db.query(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order, OrderItem.order_id == Order.id)
            .filter(Order.status != "cancelled", Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        sales_timeline.append(
            {
                "label": start.strftime("%d %b"),
                "revenue": float(point_revenue),
                "orders": int(point_orders),
                "units_sold": int(point_units),
            }
        )

    average_price = db.query(func.coalesce(func.avg(Book.price), 0)).scalar() or 0
    min_price = db.query(func.coalesce(func.min(Book.price), 0)).scalar() or 0
    max_price = db.query(func.coalesce(func.max(Book.price), 0)).scalar() or 0
    inventory_units = db.query(func.coalesce(func.sum(Book.stock_quantity), 0)).scalar() or 0
    inventory_retail_value = db.query(func.coalesce(func.sum(Book.stock_quantity * Book.price), 0)).scalar() or 0

    return {
        "range_start": range_start_date.isoformat(),
        "range_end": range_end_date.isoformat(),
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "total_books": db.query(func.count(Book.id)).scalar() or 0,
        "total_orders": total_orders,
        "total_revenue": float(revenue),
        "total_units_sold": int(total_units_sold),
        "average_order_value": round(float(average_order_value), 2),
        "revenue_today": float(revenue_today),
        "revenue_month": float(revenue_month),
        "revenue_year": float(revenue_year),
        "orders_today": int(orders_today),
        "orders_month": int(orders_month),
        "orders_year": int(orders_year),
        "pending_orders": db.query(func.count(Order.id)).filter(Order.status == "pending").scalar() or 0,
        "cancelled_orders": db.query(func.count(Order.id)).filter(Order.status == "cancelled").scalar() or 0,
        "low_stock_books": low_stock_books,
        "top_selling_books": [
            {
                "book_id": row.id,
                "title": row.title,
                "author": row.author,
                "units_sold": int(row.units_sold or 0),
                "revenue": float(row.revenue or 0),
                "stock_quantity": int(row.stock_quantity or 0),
                "price": float(row.price or 0),
            }
            for row in top_selling_rows
        ],
        "category_performance": [
            {
                "category_id": row.id,
                "category_name": row.name,
                "books_count": int(row.books_count or 0),
                "units_sold": int(row.units_sold or 0),
                "revenue": float(row.revenue or 0),
            }
            for row in category_rows
        ],
        "sales_timeline": sales_timeline,
        "pricing_overview": {
            "average_price": float(average_price),
            "min_price": float(min_price),
            "max_price": float(max_price),
            "inventory_units": int(inventory_units),
            "inventory_retail_value": float(inventory_retail_value),
        },
    }
