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


    github_webhook_secret: SecretStr
    github_client_id: str
    github_client_secret: SecretStr

    # AI providers
    nvidia_api_key: SecretStr
    nvidia_api_base_url: str = "https://integrate.api.nvidia.com/v1"
    embedding_model: str = "nvidia/nv-embed-v1"
    embedding_dimensions: int = 4096
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr

    # Security
    # Fernet symmetric key — encrypts GitHub access tokens at rest in Postgres.
    # Not an API key; generate once locally and keep stable (rotating invalidates stored tokens).
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Equivalent: base64.urlsafe_b64encode(os.urandom(32)).decode()
    fernet_key: SecretStr
    # Signs HttpOnly session cookies (itsdangerous URLSafeTimedSerializer).
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
