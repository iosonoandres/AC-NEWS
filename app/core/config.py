from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AC-NEWS Bot Backend"
    app_env: str = "development"

    telegram_bot_token: str = Field(default="")
    telegram_webhook_secret: str = Field(default="change-this-secret")
    public_base_url: str = Field(default="")

    request_timeout_seconds: float = 10.0
    news_cache_ttl_seconds: int = 300
    feedback_ttl_hours: int = 24

    users_file: Path = Path("data/users.json")
    comments_file: Path = Path("data/comments.json")
    ratings_file: Path = Path("data/ratings.json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
