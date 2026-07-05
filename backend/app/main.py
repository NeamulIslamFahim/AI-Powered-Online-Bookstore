from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.bootstrap import initialize_database
from app.db.session import engine
from app.routers import admin, auth, books, cart, categories, chat, orders, reviews, wishlist

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
initialize_database(engine, Base.metadata)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(books.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(wishlist.router)
app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/health")
def healthcheck():
    return {"success": True, "data": {"status": "ok"}, "message": "Service is healthy"}
