"""
Shared RQ queues for Meridian background work.

One worker process can listen to both:
  uv run rq worker meridian-ingest meridian-reviews
"""

from __future__ import annotations

from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from core.config import settings

INGEST_QUEUE_NAME = "meridian-ingest"
REVIEW_QUEUE_NAME = "meridian-reviews"


def redis_conn() -> Redis:
    return Redis.from_url(settings.redis_url.get_secret_value())


def ingest_queue() -> Queue:
    return Queue(INGEST_QUEUE_NAME, connection=redis_conn())


def review_queue() -> Queue:
    return Queue(REVIEW_QUEUE_NAME, connection=redis_conn())


def _clear_stale_ingest_job(repo_id: str) -> bool:
    """
    Delete finished/failed jobs with the stable id so retries can re-enqueue.
    Returns False if a job is already queued/started (caller should not enqueue).
    """
    job_id = f"ingest:{repo_id}"
    try:
        job = Job.fetch(job_id, connection=redis_conn())
    except NoSuchJobError:
        return True
    if job.is_queued or job.is_started or job.is_deferred:
        return False
    job.delete()
    return True


def enqueue_ingest_job(*, repo_id: str, access_token: str) -> str:
    """
    Enqueue durable ingest work.
    Returns "queued" or "already_running".
    Raises if Redis/RQ is unreachable.
    """
    from workers.ingest_worker import process_ingest

    if not _clear_stale_ingest_job(repo_id):
        return "already_running"

    ingest_queue().enqueue(
        process_ingest,
        repo_id,
        access_token,
        job_timeout=1800,
        result_ttl=3600,
        failure_ttl=86400,
        job_id=f"ingest:{repo_id}",
    )
    return "queued"


def ping_redis() -> bool:
    try:
        return bool(redis_conn().ping())
    except Exception:
        return False


def queue_depth() -> dict[str, int]:
    try:
        return {
            INGEST_QUEUE_NAME: ingest_queue().count,
            REVIEW_QUEUE_NAME: review_queue().count,
        }
    except Exception:
        return {INGEST_QUEUE_NAME: -1, REVIEW_QUEUE_NAME: -1}
