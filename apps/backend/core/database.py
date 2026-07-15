from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from models.tables import Base


def _database_url() -> str:
    """
    Prefer the psycopg (v3) driver. SQLAlchemy's bare postgresql://
    scheme still defaults to the legacy psycopg2 dialect.
    """
    url = settings.database_url.get_secret_value()
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql+psycopg2://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
