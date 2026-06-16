from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str

    # GitHub App
    github_app_id: str
    github_app_private_key: str
    github_webhook_secret: str
    github_client_id: str
    github_client_secret: str

    # AI Providers
    openai_api_key: str
    anthropic_api_key: str

    # Security
    fernet_key: str           # for encrypting GitHub access tokens at rest
    session_secret: str

    # App
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()

