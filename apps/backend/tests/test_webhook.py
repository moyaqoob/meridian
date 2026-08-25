"""Webhook route tests — HMAC, dedup, enqueue."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from core.config import settings


def _sign(body: bytes) -> str:
    secret = settings.github_webhook_secret.get_secret_value().encode()
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _post_webhook(
    client: TestClient,
    payload: dict[str, Any],
    *,
    delivery: str = "delivery-1",
    event: str = "pull_request",
    signature: str | None = None,
) -> Any:
    body = json.dumps(payload).encode()
    headers = {
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": event,
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature if signature is not None else _sign(body),
    }
    return client.post("/webhook/github", content=body, headers=headers)


def test_webhook_rejects_bad_signature(client: TestClient) -> None:
    payload = {"action": "opened", "pull_request": {"number": 1}}
    response = _post_webhook(client, payload, signature="sha256=deadbeef")
    assert response.status_code == 401


def test_webhook_ignores_non_pr_events(client: TestClient) -> None:
    fake_redis = MagicMock()
    fake_redis.set.return_value = True
    with patch("routers.webhook._redis", return_value=fake_redis):
        response = _post_webhook(
            client,
            {"action": "push", "ref": "refs/heads/main"},
            event="push",
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_ignores_non_actionable_pr_actions(
    client: TestClient,
    mock_db: MagicMock,
) -> None:
    fake_redis = MagicMock()
    fake_redis.set.return_value = True
    payload = {
        "action": "closed",
        "pull_request": {
            "number": 3,
            "head": {"sha": "abc"},
        },
        "repository": {"id": 1001},
    }
    with patch("routers.webhook._redis", return_value=fake_redis):
        response = _post_webhook(client, payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "action=closed"}


def test_webhook_dedups_delivery(client: TestClient) -> None:
    fake_redis = MagicMock()
    fake_redis.set.return_value = False  # already present
    payload = {
        "action": "opened",
        "pull_request": {"number": 3, "head": {"sha": "abc"}},
        "repository": {"id": 1001},
    }
    with patch("routers.webhook._redis", return_value=fake_redis):
        response = _post_webhook(client, payload, delivery="dup-1")
    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"
    fake_redis.set.assert_called_once()


def test_webhook_enqueues_review(
    client: TestClient,
    mock_db: MagicMock,
) -> None:
    fake_redis = MagicMock()
    fake_redis.set.return_value = True

    repo = MagicMock()
    repo.id = "repo-1"
    repo.full_name = "tester/demo-repo"
    repo.ingest_status = "ready"
    mock_db.one_or_none.return_value = repo

    enqueue_result = MagicMock(
        review_id=None,
        status="queued",
        head_sha="abc123",
        message="Review job enqueued",
    )

    payload = {
        "action": "opened",
        "pull_request": {
            "number": 3,
            "head": {"sha": "abc123"},
        },
        "repository": {"id": 1001, "name": "demo-repo", "owner": {"login": "tester"}},
    }

    with (
        patch("routers.webhook._redis", return_value=fake_redis),
        patch(
            "routers.webhook.enqueue_review_job",
            return_value=enqueue_result,
        ) as enqueue,
    ):
        response = _post_webhook(client, payload, delivery="delivery-new")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["head_sha"] == "abc123"
    enqueue.assert_called_once()
    assert enqueue.call_args.kwargs["repo_id"] == "repo-1"
    assert enqueue.call_args.kwargs["pr_number"] == 3
    assert enqueue.call_args.kwargs["head_sha"] == "abc123"
