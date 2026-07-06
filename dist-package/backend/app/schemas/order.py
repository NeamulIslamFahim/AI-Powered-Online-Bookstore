from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.book import BookResponse
from app.schemas.common import ORMBase
from app.schemas.user import UserResponse


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "paid", "shipped", "delivered", "cancelled"]


class OrderItemResponse(ORMBase):
    id: int
    quantity: int
    price_at_purchase: float
    book: BookResponse


class OrderResponse(ORMBase):
    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: datetime
    items: list[OrderItemResponse]
    user: UserResponse | None = None


class AdminTopBookResponse(BaseModel):
    book_id: int
    title: str
    author: str
    units_sold: int
    revenue: float
    stock_quantity: int
    price: float


class AdminCategoryPerformanceResponse(BaseModel):
    category_id: int | None = None
    category_name: str
    books_count: int
    units_sold: int
    revenue: float


class AdminSalesPointResponse(BaseModel):
    label: str
    revenue: float
    orders: int
    units_sold: int


class AdminPricingOverviewResponse(BaseModel):
    average_price: float
    min_price: float
    max_price: float
    inventory_units: int
    inventory_retail_value: float


class AdminStatsResponse(BaseModel):
    range_start: str
    range_end: str
    total_users: int
    total_books: int
    total_orders: int
    total_revenue: float
    total_units_sold: int
    average_order_value: float
    revenue_today: float
    revenue_month: float
    revenue_year: float
    orders_today: int
    orders_month: int
    orders_year: int
    pending_orders: int
    cancelled_orders: int
    low_stock_books: list[BookResponse]
    top_selling_books: list[AdminTopBookResponse]
    category_performance: list[AdminCategoryPerformanceResponse]
    sales_timeline: list[AdminSalesPointResponse]
    pricing_overview: AdminPricingOverviewResponse
