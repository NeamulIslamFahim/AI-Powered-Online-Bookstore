from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import create_category, get_categories

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse])
def list_all_categories(db: Session = Depends(get_db)):
    return get_categories(db)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create(payload: CategoryCreate, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    return create_category(db, payload)

