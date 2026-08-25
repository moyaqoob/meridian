"""SSE stream for live review pipeline progress via Redis Streams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import SessionLocal, get_db
from models.tables import PR, Repo, Review, User
from routers.auth import get_current_user
from services import pipeline_events

router = APIRouter(prefix="/api/pr", tags=["review-stream"])


def _format_sse(event: str, data: dict, *, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def _load_review_status(review_id: str) -> tuple[str | None, str | None]:
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None:
            return None, None
        return review.status, review.error_message
    finally:
        db.close()


def _complete_payload_from_db(review_id: str) -> dict | None:
    from workers.review_worker import _review_to_out

    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is None or review.status != "complete":
            return None
        out = _review_to_out(review)
        return {
            "review_id": out.review_id,
            "status": "complete",
            "summary": out.summary,
            "findings": [f.model_dump() for f in out.findings],
            "timings": out.timings,
        }
    finally:
        db.close()


@router.get("/{review_id}/review/stream")
async def stream_review(
    review_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    pr = db.get(PR, review.pr_id)
    if pr is None:
        raise HTTPException(status_code=404, detail="PR not found")
    repo = db.get(Repo, pr.repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Review not found")

    async def event_generator() -> AsyncIterator[str]:
        last_id = "0-0"
        terminal = False

        for entry_id, event, data in await asyncio.to_thread(
            pipeline_events.read_all_events, review_id
        ):
            last_id = entry_id
            yield _format_sse(event, data, event_id=entry_id)
            if event in ("complete", "error"):
                terminal = True

        if terminal:
            return

        status, error_message = await asyncio.to_thread(_load_review_status, review_id)
        if status == "complete":
            payload = await asyncio.to_thread(_complete_payload_from_db, review_id)
            if payload:
                yield _format_sse("complete", payload)
            return
        if status == "error":
            yield _format_sse(
                "error",
                {
                    "stage": "generation",
                    "message": error_message or "Review failed",
                    "retryable": True,
                },
            )
            return

        while True:
            entries = await asyncio.to_thread(
                pipeline_events.read_new_events,
                review_id,
                last_id,
                block_ms=15000,
            )
            if not entries:
                yield ": keepalive\n\n"
                status, error_message = await asyncio.to_thread(
                    _load_review_status, review_id
                )
                if status not in ("complete", "error"):
                    continue
                for entry_id, event, data in await asyncio.to_thread(
                    pipeline_events.read_all_events, review_id
                ):
                    if entry_id <= last_id:
                        continue
                    last_id = entry_id
                    yield _format_sse(event, data, event_id=entry_id)
                    if event in ("complete", "error"):
                        return
                if status == "complete":
                    payload = await asyncio.to_thread(
                        _complete_payload_from_db, review_id
                    )
                    if payload:
                        yield _format_sse("complete", payload)
                else:
                    yield _format_sse(
                        "error",
                        {
                            "stage": "generation",
                            "message": error_message or "Review failed",
                            "retryable": True,
                        },
                    )
                return

            for entry_id, event, data in entries:
                last_id = entry_id
                yield _format_sse(event, data, event_id=entry_id)
                if event in ("complete", "error"):
                    return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
