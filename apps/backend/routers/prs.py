"""Pull request browse + review trigger (enqueue → SSE)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from models.schemas import (
    PullFileOut,
    PullRequestDetailOut,
    PullRequestOut,
    ReviewJobOut,
    ReviewOut,
)
from models.tables import PR, Repo, Review, User
from routers.auth import decrypt_access_token, get_current_user
from services import github as github_service
from services.review_queue import enqueue_review_job, find_existing_review
from workers.review_worker import _review_to_out

router = APIRouter(prefix="/api/prs", tags=["prs"])


def _full_name(owner: str, repo: str) -> str:
    return f"{owner}/{repo}"


def _pr_summary(item: dict) -> PullRequestOut:
    user = item.get("user") or {}
    base = item.get("base") or {}
    head = item.get("head") or {}
    return PullRequestOut(
        number=int(item["number"]),
        title=str(item.get("title") or ""),
        state=str(item.get("state") or "open"),
        author=str(user.get("login") or ""),
        html_url=str(item.get("html_url") or ""),
        updated_at=str(item.get("updated_at") or ""),
        base_branch=str(base.get("ref") or ""),
        head_branch=str(head.get("ref") or ""),
        additions=int(item.get("additions") or 0),
        deletions=int(item.get("deletions") or 0),
        changed_files=int(item.get("changed_files") or 0),
    )


def _get_ready_repo(db: Session, user: User, owner: str, repo: str) -> Repo:
    full_name = _full_name(owner, repo)
    row = (
        db.query(Repo)
        .filter(Repo.user_id == user.id, Repo.full_name == full_name)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Repo not connected to Meridian")
    if row.ingest_status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Repo ingest status is '{row.ingest_status}'. Ingest must be ready before review.",
        )
    return row


def _job_out_from_review(review: Review, *, head_sha: str, message: str) -> ReviewJobOut:
    status = review.status  # type: ignore[assignment]
    review_out: ReviewOut | None = None
    if review.status == "complete":
        review_out = _review_to_out(review)
        status = "complete"
    elif review.status == "error":
        status = "error"
        message = review.error_message or message
    elif review.status in ("pending", "running"):
        status = "running"
    return ReviewJobOut(
        status=status,  # type: ignore[arg-type]
        review_id=review.id,
        pr_id=review.pr_id,
        head_sha=head_sha,
        message=message,
        review=review_out,
    )


@router.get("/{owner}/{repo}", response_model=list[PullRequestOut])
async def list_pull_requests(
    owner: str,
    repo: str,
    user: User = Depends(get_current_user),
) -> list[PullRequestOut]:
    """List open pull requests for a repository (newest updated first)."""
    token = decrypt_access_token(user.encrypted_access_token)
    remote = await github_service.list_pull_requests(token, _full_name(owner, repo))
    return [_pr_summary(item) for item in remote]


@router.get("/{owner}/{repo}/{number}", response_model=PullRequestDetailOut)
async def get_pull_request(
    owner: str,
    repo: str,
    number: int,
    user: User = Depends(get_current_user),
) -> PullRequestDetailOut:
    """Fetch PR metadata, changed files, and unified diff."""
    if number < 1:
        raise HTTPException(status_code=400, detail="PR number must be >= 1")

    token = decrypt_access_token(user.encrypted_access_token)
    full_name = _full_name(owner, repo)

    pr, diff, files = await asyncio.gather(
        github_service.get_pull_request(token, full_name, number),
        github_service.get_pull_diff(token, full_name, number),
        github_service.list_pull_files(token, full_name, number),
    )

    summary = _pr_summary(pr)
    return PullRequestDetailOut(
        **summary.model_dump(),
        body=pr.get("body"),
        diff=diff,
        files=[
            PullFileOut(
                filename=str(f.get("filename") or ""),
                status=str(f.get("status") or "modified"),
                additions=int(f.get("additions") or 0),
                deletions=int(f.get("deletions") or 0),
            )
            for f in files
            if f.get("filename")
        ],
    )


@router.get("/{owner}/{repo}/{number}/review", response_model=ReviewJobOut)
async def get_review_status(
    owner: str,
    repo: str,
    number: int,
    head_sha: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewJobOut:
    """Look up the review for a PR (optionally pinned to head_sha)."""
    if number < 1:
        raise HTTPException(status_code=400, detail="PR number must be >= 1")

    tracked = _get_ready_repo(db, user, owner, repo)
    sha = head_sha
    if not sha:
        token = decrypt_access_token(user.encrypted_access_token)
        pr = await github_service.get_pull_request(
            token, _full_name(owner, repo), number
        )
        sha = str((pr.get("head") or {}).get("sha") or "")
    if not sha:
        raise HTTPException(status_code=404, detail="No review found")

    existing = find_existing_review(
        db, repo_id=tracked.id, pr_number=number, head_sha=sha
    )
    if existing is None:
        # Fall back to latest review for this PR number.
        pr_row = (
            db.query(PR)
            .filter(PR.repo_id == tracked.id, PR.number == number)
            .one_or_none()
        )
        if pr_row is None:
            raise HTTPException(status_code=404, detail="No review found")
        existing = (
            db.query(Review)
            .filter(Review.pr_id == pr_row.id)
            .order_by(Review.created_at.desc())
            .first()
        )
        if existing is None:
            raise HTTPException(status_code=404, detail="No review found")
        sha = existing.head_sha

    return _job_out_from_review(
        existing,
        head_sha=sha,
        message="Review status",
    )


@router.post("/{owner}/{repo}/{number}/review", response_model=ReviewJobOut)
async def review_pull_request(
    owner: str,
    repo: str,
    number: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewJobOut:
    """
    Enqueue retrieval + generation for a PR (same job as the webhook path).
    Returns immediately; subscribe to the SSE stream for live progress.
    """
    if number < 1:
        raise HTTPException(status_code=400, detail="PR number must be >= 1")

    tracked = _get_ready_repo(db, user, owner, repo)
    token = decrypt_access_token(user.encrypted_access_token)
    full_name = _full_name(owner, repo)

    pr = await github_service.get_pull_request(token, full_name, number)
    head_sha = str((pr.get("head") or {}).get("sha") or "")
    if not head_sha:
        raise HTTPException(status_code=502, detail="PR head SHA missing from GitHub")

    result = enqueue_review_job(
        db,
        repo_id=tracked.id,
        pr_number=number,
        head_sha=head_sha,
    )

    if result.status == "exists" and result.review_id:
        review = db.get(Review, result.review_id)
        if review is not None:
            return _job_out_from_review(
                review,
                head_sha=head_sha,
                message=result.message,
            )

    return ReviewJobOut(
        status="queued",
        review_id=result.review_id,
        pr_id=result.pr_id,
        head_sha=head_sha,
        message=result.message,
        review=None,
    )
