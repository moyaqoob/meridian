"""
Shared review job enqueue + idempotency (layer 1).

Webhook and manual trigger both call enqueue_review_job → process_review.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.tables import PR, Review
from services.job_queue import REVIEW_QUEUE_NAME, redis_conn, review_queue

LOCK_TTL_SECONDS = 300

# Re-export for callers/tests that import from this module.
__all__ = [
    "EnqueueResult",
    "LOCK_TTL_SECONDS",
    "REVIEW_QUEUE_NAME",
    "enqueue_review_job",
    "find_existing_review",
    "lock_key",
    "redis_conn",
    "review_queue",
]


@dataclass
class EnqueueResult:
    review_id: str | None
    pr_id: str | None
    status: str  # "exists" | "queued" | "skipped"
    head_sha: str
    message: str


def lock_key(repo_id: str, pr_number: int, head_sha: str) -> str:
    return f"review-lock:{repo_id}:{pr_number}:{head_sha}"


def find_existing_review(
    db: Session,
    *,
    repo_id: str,
    pr_number: int,
    head_sha: str,
) -> Review | None:
    """Idempotency layer 1: (repo_id, pr_number, head_sha) via PR join."""
    return (
        db.query(Review)
        .join(PR, Review.pr_id == PR.id)
        .filter(
            PR.repo_id == repo_id,
            PR.number == pr_number,
            Review.head_sha == head_sha,
        )
        .one_or_none()
    )


def _is_terminal_or_inflight(review: Review) -> bool:
    """Complete/running rows are idempotent; error rows may be retried."""
    return review.status in ("complete", "running", "pending")


def enqueue_review_job(
    db: Session,
    *,
    repo_id: str,
    pr_number: int,
    head_sha: str,
) -> EnqueueResult:
    """
    If a review already exists for this SHA, return it.
    Otherwise enqueue process_review. Does not create Review rows (worker does).
    """
    existing = find_existing_review(
        db,
        repo_id=repo_id,
        pr_number=pr_number,
        head_sha=head_sha,
    )
    if existing is not None and _is_terminal_or_inflight(existing):
        return EnqueueResult(
            review_id=existing.id,
            pr_id=existing.pr_id,
            status="exists" if existing.status == "complete" else "running",
            head_sha=head_sha,
            message="Review already exists for this head SHA",
        )

    # Failed reviews may be retried for the same head SHA.
    retry_review_id = existing.id if existing is not None else None
    retry_pr_id = existing.pr_id if existing is not None else None

    # Import inside function so RQ workers can import this module without
    # circular import at module load, and so the job path is always the worker fn.
    from workers.review_worker import process_review

    review_queue().enqueue(
        process_review,
        repo_id,
        pr_number,
        head_sha,
        job_timeout=600,
        result_ttl=3600,
        failure_ttl=86400,
    )
    return EnqueueResult(
        review_id=retry_review_id,
        pr_id=retry_pr_id,
        status="queued",
        head_sha=head_sha,
        message="Review job enqueued",
    )
