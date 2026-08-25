"""
Redis Streams event log for live review pipeline SSE.

Keyed as review:{review_id}:events — replayable via XRANGE, live via XREAD BLOCK.
"""

from __future__ import annotations

import json
from typing import Any

from core.helper import _redis

STREAM_TTL_SECONDS = 60 * 60
STREAM_MAXLEN = 500


def stream_key(review_id: str) -> str:
    return f"review:{review_id}:events"


def _xadd(review_id: str, event: str, data: dict[str, Any]) -> str:
    r = _redis()
    key = stream_key(review_id)
    entry_id = r.xadd(
        key,
        {"event": event, "data": json.dumps(data)},
        maxlen=STREAM_MAXLEN,
        approximate=True,
    )
    # Refresh TTL on every write so active reviews don't expire mid-stream.
    r.expire(key, STREAM_TTL_SECONDS)
    return entry_id


def emit_stage_update(
    review_id: str,
    *,
    stage: str,
    progress: float,
    message: str,
    duration_ms: float | None = None,
) -> None:
    payload: dict[str, Any] = {
        "stage": stage,
        "progress": progress,
        "message": message,
    }
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    _xadd(review_id, "stage-update", payload)


def emit_generation_chunk(review_id: str, *, text: str, phase: str = "summary") -> None:
    _xadd(review_id, "generation-chunk", {"text": text, "phase": phase})


def emit_complete(review_id: str, data: dict[str, Any]) -> None:
    _xadd(review_id, "complete", data)


def emit_error(
    review_id: str,
    *,
    stage: str,
    message: str,
    retryable: bool = False,
) -> None:
    _xadd(
        review_id,
        "error",
        {"stage": stage, "message": message, "retryable": retryable},
    )


def read_all_events(review_id: str) -> list[tuple[str, str, dict[str, Any]]]:
    """Return [(entry_id, event_name, data), ...] in order."""
    r = _redis()
    entries = r.xrange(stream_key(review_id), min="-", max="+")
    out: list[tuple[str, str, dict[str, Any]]] = []
    for entry_id, fields in entries:
        event = fields.get("event") or "message"
        raw = fields.get("data") or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"raw": raw}
        if not isinstance(data, dict):
            data = {"value": data}
        out.append((entry_id, event, data))
    return out


def read_new_events(
    review_id: str,
    last_id: str,
    *,
    block_ms: int = 15000,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Block-read new entries after last_id. Returns [] on timeout."""
    r = _redis()
    key = stream_key(review_id)
    result = r.xread({key: last_id}, count=50, block=block_ms)
    if not result:
        return []

    out: list[tuple[str, str, dict[str, Any]]] = []
    for _stream, entries in result:
        for entry_id, fields in entries:
            event = fields.get("event") or "message"
            raw = fields.get("data") or "{}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw": raw}
            if not isinstance(data, dict):
                data = {"value": data}
            out.append((entry_id, event, data))
    return out
