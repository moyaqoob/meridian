"""
RQ worker: process_review(repo_id, pr_number, head_sha).

Fetch diff → retrieve → generate → persist Review + annotations → emit SSE events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.helper import decrypt_access_token
from models.schemas import ReviewOut
from models.tables import PR, Repo, Review, ReviewAnnotation, User
from services import github as github_service
from services import pipeline_events
from services.retrieval import retrieve_chunks
from services.review_gen import generate_review
from services.review_queue import LOCK_TTL_SECONDS, find_existing_review, lock_key, redis_conn

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _run(coro):
    return asyncio.run(coro)


def _persist_review_result(
    db: Session,
    *,
    review: Review,
    out: ReviewOut,
) -> None:
    review.status = "complete"
    review.summary = out.summary
    review.structured_json = json.dumps(
        {
            "summary": out.summary,
            "pr_type": out.pr_type,
            "findings": [f.model_dump() for f in out.findings],
            "timings": out.timings,
        }
    )
    review.model_version = out.model_version
    review.error_message = None

    db.query(ReviewAnnotation).filter(ReviewAnnotation.review_id == review.id).delete(
        synchronize_session=False
    )
    for finding in out.findings:
        db.add(
            ReviewAnnotation(
                id=str(uuid.uuid4()),
                review_id=review.id,
                file_path=finding.file_path or "",
                line_start=0,
                line_end=0,
                comment=f"{finding.title}: {finding.comment}",
                severity=finding.severity,
                category=finding.category,
            )
        )


def _review_to_out(review: Review) -> ReviewOut:
    data: dict = {}
    if review.structured_json:
        try:
            data = json.loads(review.structured_json)
        except json.JSONDecodeError:
            data = {}
    findings = data.get("findings") or []
    return ReviewOut(
        review_id=review.id,
        pr_id=review.pr_id,
        summary=review.summary or str(data.get("summary") or ""),
        pr_type=data.get("pr_type") or "chore",
        findings=findings,
        model_version=review.model_version or "",
        timings=data.get("timings") or {},
    )


def _upsert_pr(
    db: Session,
    *,
    repo_id: str,
    github_pr: dict,
    head_sha: str,
) -> PR:
    number = int(github_pr["number"])
    row = (
        db.query(PR)
        .filter(PR.repo_id == repo_id, PR.number == number)
        .one_or_none()
    )
    base = github_pr.get("base") or {}
    if row is None:
        row = PR(
            id=str(uuid.uuid4()),
            repo_id=repo_id,
            github_pr_id=int(github_pr.get("id") or number),
            number=number,
            title=str(github_pr.get("title") or ""),
            head_sha=head_sha,
            base_sha=str(base.get("sha") or ""),
            status="running",
        )
        db.add(row)
    else:
        row.github_pr_id = int(github_pr.get("id") or row.github_pr_id)
        row.title = str(github_pr.get("title") or row.title)
        row.head_sha = head_sha
        row.base_sha = str(base.get("sha") or row.base_sha)
        row.status = "running"
    db.flush()
    return row


def process_review(repo_id: str, pr_number: int, head_sha: str) -> str | None:
    """
    RQ job entrypoint. Returns review_id on success, None if skipped.
    """
    r = redis_conn()
    key = lock_key(repo_id, pr_number, head_sha)
    acquired = r.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS)
    if not acquired:
        logger.info(
            "review lock held; skipping repo=%s pr=%s sha=%s",
            repo_id,
            pr_number,
            head_sha,
        )
        return None

    db: Session = SessionLocal()
    review: Review | None = None
    stage = "validation"
    try:
        existing = find_existing_review(
            db,
            repo_id=repo_id,
            pr_number=pr_number,
            head_sha=head_sha,
        )
        if existing is not None:
            if existing.status == "complete":
                return existing.id
            if existing.status in ("running", "pending"):
                # Another worker already created the row — attach to it if still running.
                review = existing
            elif existing.status == "error":
                # Retry path: reuse the same (pr_id, head_sha) row.
                review = existing
                review.status = "running"
                review.error_message = None

        repo = db.get(Repo, repo_id)
        if repo is None:
            logger.error("repo not found: %s", repo_id)
            return None
        if repo.ingest_status != "ready":
            logger.error("repo %s ingest_status=%s", repo_id, repo.ingest_status)
            return None

        user = db.get(User, repo.user_id)
        if user is None:
            logger.error("user not found for repo %s", repo_id)
            return None

        token = decrypt_access_token(user.encrypted_access_token)
        full_name = repo.full_name

        github_pr, diff = _run(
            asyncio.gather(
                github_service.get_pull_request(token, full_name, pr_number),
                github_service.get_pull_diff(token, full_name, pr_number),
            )
        )
        remote_sha = str((github_pr.get("head") or {}).get("sha") or head_sha)
        if remote_sha != head_sha:
            # Prefer the SHA we were asked to review; warn but continue with requested.
            logger.warning(
                "head_sha mismatch requested=%s remote=%s",
                head_sha,
                remote_sha,
            )

        pr_row = _upsert_pr(db, repo_id=repo_id, github_pr=github_pr, head_sha=head_sha)

        if review is None:
            review = Review(
                id=str(uuid.uuid4()),
                pr_id=pr_row.id,
                head_sha=head_sha,
                status="running",
                created_at=_utcnow(),
            )
            db.add(review)
            db.flush()
        else:
            review.status = "running"
            review.error_message = None

        db.commit()
        review_id = review.id

        t_val = time.perf_counter()
        pipeline_events.emit_stage_update(
            review_id,
            stage="validation",
            progress=0.15,
            message=f"Validated PR #{pr_number}",
            duration_ms=(time.perf_counter() - t_val) * 1000,
        )

        stage = "retrieval"
        pipeline_events.emit_stage_update(
            review_id,
            stage="retrieval",
            progress=0.35,
            message="Retrieving relevant code chunks",
        )
        t0 = time.perf_counter()
        chunks = _run(
            retrieve_chunks(
                db,
                repo_id=repo_id,
                diff=diff,
                pr_title=str(github_pr.get("title") or ""),
            )
        )
        retrieval_s = time.perf_counter() - t0
        pipeline_events.emit_stage_update(
            review_id,
            stage="retrieval",
            progress=0.55,
            message=f"Retrieved {len(chunks)} chunks",
            duration_ms=retrieval_s * 1000,
        )

        stage = "generation"
        pipeline_events.emit_stage_update(
            review_id,
            stage="generation",
            progress=0.65,
            message="Generating review",
        )

        async def on_chunk(text: str) -> None:
            pipeline_events.emit_generation_chunk(review_id, text=text, phase="summary")

        t1 = time.perf_counter()
        out = _run(
            generate_review(
                pr_id=pr_row.id,
                diff=diff,
                chunks=chunks,
                on_chunk=on_chunk,
            )
        )
        generation_s = time.perf_counter() - t1
        out.review_id = review_id
        out.timings = {"retrieval": retrieval_s, "generation": generation_s}

        stage = "citation-mapping"
        pipeline_events.emit_stage_update(
            review_id,
            stage="citation-mapping",
            progress=0.9,
            message="Persisting findings",
        )

        _persist_review_result(db, review=review, out=out)
        pr_row.status = "reviewed"
        db.commit()

        complete_payload = {
            "review_id": review_id,
            "status": "complete",
            "summary": out.summary,
            "findings": [f.model_dump() for f in out.findings],
            "timings": out.timings,
        }
        pipeline_events.emit_stage_update(
            review_id,
            stage="complete",
            progress=1.0,
            message="Review complete",
        )
        pipeline_events.emit_complete(review_id, complete_payload)
        return review_id

    except Exception as exc:
        logger.exception(
            "process_review failed repo=%s pr=%s sha=%s",
            repo_id,
            pr_number,
            head_sha,
        )
        if review is not None:
            try:
                review.status = "error"
                review.error_message = str(exc)
                pr_row = db.get(PR, review.pr_id)
                if pr_row is not None:
                    pr_row.status = "failed"
                db.commit()
                pipeline_events.emit_error(
                    review.id,
                    stage=stage,
                    message=str(exc),
                    retryable=True,
                )
            except Exception:
                db.rollback()
                logger.exception("failed to persist review error state")
        return None
    finally:
        db.close()
        r.delete(key)
