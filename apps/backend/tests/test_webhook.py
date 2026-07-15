"""Webhook route tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_webhook_ignores_non_pr_events(client: TestClient) -> None:
    response = client.post("/webhook/github", json={"action": "push", "ref": "refs/heads/main"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "ignored",
        "reason": "not a pull request event",
    }


def test_webhook_fetches_pull_request(client: TestClient) -> None:
    pr_payload = {
        "number": 3,
        "title": "Wire webhook",
        "state": "open",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = pr_payload
    mock_response.text = "{}"

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    payload: dict[str, Any] = {
        "action": "opened",
        "pull_request": {"number": 3},
        "repository": {
            "name": "demo-repo",
            "owner": {"login": "tester"},
        },
    }

    with patch("routers.webhook.httpx.AsyncClient", return_value=mock_client):
        response = client.post("/webhook/github", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "opened"
    assert body["pull_request"]["number"] == 3
    mock_client.get.assert_awaited_once()
    called_url = mock_client.get.await_args.args[0]
    assert called_url == "https://api.github.com/repos/tester/demo-repo/pulls/3"


def test_webhook_returns_404_when_pr_missing(client: TestClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.is_success = False
    mock_response.text = "Not Found"

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    payload = {
        "action": "opened",
        "pull_request": {"number": 99},
        "repository": {
            "name": "demo-repo",
            "owner": {"login": "tester"},
        },
    }

    with patch("routers.webhook.httpx.AsyncClient", return_value=mock_client):
        response = client.post("/webhook/github", json=payload)

    assert response.status_code == 404
