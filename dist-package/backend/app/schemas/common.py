from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str | list[dict]


class PaginatedMeta(BaseModel):
    total: int
    page: int
    pages: int
