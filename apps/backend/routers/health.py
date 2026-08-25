"""System health — DB, Redis, queue reachability."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from core.database import engine
from services.job_queue import ping_redis, queue_depth

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    db_ok = False
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc)[:200]

    redis_ok = ping_redis()
    queues = queue_depth() if redis_ok else {}

    ok = db_ok and redis_ok
    return {
        "status": "ok" if ok else "degraded",
        "database": {"ok": db_ok, "error": db_error},
        "redis": {"ok": redis_ok},
        "queues": queues,
        "hint": None
        if ok
        else (
            "Start Docker (Postgres + Redis), then run the API and "
            "`uv run rq worker meridian-ingest meridian-reviews`."
        ),
    }
