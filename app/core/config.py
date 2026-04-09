from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    PROJECT_NAME: str = "Online Bookstore API"
    DATABASE_URL: str = "mysql+pymysql://root:@127.0.0.1:3306/online_bookstore"
    JWT_SECRET_KEY: str = Field(
        default="change-this-secret",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    N8N_CHAT_WEBHOOK_URL: str | None = None
    ASSISTANT_TEMPERATURE: float = Field(default=0.5, ge=0, le=2)
    LOW_STOCK_THRESHOLD: int = 5
    ADMIN_NAME: str = "Store Admin"
    ADMIN_EMAIL: str = "admin@onlinebookstore.com"
    ADMIN_PASSWORD: str = "Admin12345"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
