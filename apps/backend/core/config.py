from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "Meridian"
    environment: Literal[
        "development",
        "staging",
        "production",
        "test",
    ] = "development"

    debug: bool = False
    log_level: str = "INFO"

    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: SecretStr

    # Redis
    redis_url: SecretStr

    # GitHub App
    github_app_id: str
    github_app_private_key: SecretStr
    github_webhook_secret: SecretStr
    github_client_id: str
    github_client_secret: SecretStr

    # AI providers
    openai_api_key: SecretStr
    anthropic_api_key: SecretStr

    # Security
    fernet_key: SecretStr
    session_secret: SecretStr

    # Sessions
    session_max_age_seconds: int = 60 * 60 * 24 * 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
