from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.category import Category
from app.schemas.category import CategoryCreate


def get_categories(db: Session):
    return db.query(Category).order_by(Category.name.asc()).all()


def create_category(db: Session, payload: CategoryCreate):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise AppException(400, "Category already exists")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

