"""
GitHub webhook receiver.

Must return in under 2s: verify HMAC, Redis dedup, enqueue, return.
No embeddings, no LLM, no review DB writes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.helper import _redis
from models.tables import Repo
from services.review_queue import enqueue_review_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

DELIVERY_TTL_SECONDS = 60 * 60 * 24
ACTIONABLE = {"opened", "synchronize", "reopened"}


def _verify_signature(body: bytes, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")

    secret = settings.github_webhook_secret.get_secret_value().encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/github")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
) -> dict:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if not x_github_delivery:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Delivery")

    redis = _redis()
    dedup_key = f"github:delivery:{x_github_delivery}"
    # SETNX — if already seen, acknowledge without reprocessing.
    if not redis.set(dedup_key, "1", nx=True, ex=DELIVERY_TTL_SECONDS):
        return {"status": "duplicate", "delivery": x_github_delivery}

    if x_github_event and x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event={x_github_event}"}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if "pull_request" not in payload:
        return {"status": "ignored", "reason": "not a pull request event"}

    action = payload.get("action")
    if action not in ACTIONABLE:
        return {"status": "ignored", "reason": f"action={action}"}

    pr = payload["pull_request"]
    repository = payload.get("repository") or {}
    github_repo_id = repository.get("id")
    pr_number = pr.get("number")
    head_sha = (pr.get("head") or {}).get("sha")

    if github_repo_id is None or pr_number is None or not head_sha:
        return {"status": "ignored", "reason": "missing repo/pr/sha"}

    repo = (
        db.query(Repo)
        .filter(Repo.github_repo_id == int(github_repo_id))
        .one_or_none()
    )
    if repo is None:
        return {"status": "ignored", "reason": "repo not connected"}

    if repo.ingest_status != "ready":
        return {"status": "ignored", "reason": f"ingest_status={repo.ingest_status}"}

    result = enqueue_review_job(
        db,
        repo_id=repo.id,
        pr_number=int(pr_number),
        head_sha=str(head_sha),
    )
    logger.info(
        "webhook enqueued delivery=%s repo=%s pr=%s status=%s",
        x_github_delivery,
        repo.full_name,
        pr_number,
        result.status,
    )
    return {
        "status": result.status,
        "review_id": result.review_id,
        "head_sha": result.head_sha,
        "message": result.message,
    }
