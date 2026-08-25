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


def _add_unique_constraint_if_missing(
    conn,
    *,
    table: str,
    constraint: str,
    columns: str,
) -> None:
    """Idempotent constraint add — create_all may have already created it."""
    conn.execute(
        text(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{constraint}'
                ) THEN
                    ALTER TABLE {table}
                        ADD CONSTRAINT {constraint} UNIQUE ({columns});
                END IF;
            END $$;
            """
        )
    )


def _ensure_phase2_columns(conn) -> None:
    """
    create_all does not ALTER existing tables. Add columns/constraints needed
    for Phase 2 on databases that already existed from Phase 1.
    """
    statements = [
        """
        DO $$ BEGIN
            CREATE TYPE review_status_enum AS ENUM
                ('pending', 'running', 'complete', 'error');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
            CREATE TYPE dependency_edge_type_enum AS ENUM
                ('import', 'reexport', 'external');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """,
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS head_sha VARCHAR",
        """
        ALTER TABLE reviews ADD COLUMN IF NOT EXISTS status review_status_enum
            NOT NULL DEFAULT 'complete'
        """,
        "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ALTER TABLE reviews ALTER COLUMN summary DROP NOT NULL",
        "ALTER TABLE reviews ALTER COLUMN structured_json DROP NOT NULL",
        "ALTER TABLE reviews ALTER COLUMN model_version DROP NOT NULL",
        """
        UPDATE reviews SET head_sha = COALESCE(head_sha, '')
        WHERE head_sha IS NULL
        """,
    ]
    for stmt in statements:
        conn.execute(text(stmt))

    _add_unique_constraint_if_missing(
        conn,
        table="reviews",
        constraint="uq_reviews_pr_head_sha",
        columns="pr_id, head_sha",
    )
    _add_unique_constraint_if_missing(
        conn,
        table="prs",
        constraint="uq_prs_repo_number",
        columns="repo_id, number",
    )


def _recover_stale_ingests(conn) -> None:
    """Deprecated: ingest is RQ-backed and survives API restart."""
    return


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _ensure_phase2_columns(conn)
    # Do NOT auto-fail processing repos on API restart — ingest runs in RQ
    # and survives uvicorn reload. Zombies are cleared via Retry ingest.


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
