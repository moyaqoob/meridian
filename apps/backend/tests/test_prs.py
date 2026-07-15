"""PR route tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_list_pulls_requires_auth(client: TestClient) -> None:
    response = client.get("/api/prs/tester/demo-repo")
    assert response.status_code == 401


def test_list_pulls(
    auth_client: TestClient,
    sample_pull: dict[str, Any],
) -> None:
    with patch(
        "routers.prs.github_service.list_pull_requests",
        new=AsyncMock(return_value=[sample_pull]),
    ):
        response = auth_client.get("/api/prs/tester/demo-repo")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["number"] == 7
    assert body[0]["title"] == "Add session hardening"
    assert body[0]["author"] == "tester"
    assert body[0]["base_branch"] == "main"
    assert body[0]["head_branch"] == "feat/auth"


def test_get_pull_detail(
    auth_client: TestClient,
    sample_pull: dict[str, Any],
) -> None:
    files = [
        {
            "filename": "apps/web/lib/auth/session.ts",
            "status": "modified",
            "additions": 10,
            "deletions": 2,
        },
        {
            "filename": "apps/backend/routers/auth.py",
            "status": "modified",
            "additions": 2,
            "deletions": 1,
        },
    ]
    diff = (
        "diff --git a/apps/web/lib/auth/session.ts b/apps/web/lib/auth/session.ts\n"
        "--- a/apps/web/lib/auth/session.ts\n"
        "+++ b/apps/web/lib/auth/session.ts\n"
        "@@ -1,2 +1,3 @@\n"
        " export async function getSession() {\n"
        "+  return null\n"
        " }\n"
    )

    with (
        patch(
            "routers.prs.github_service.get_pull_request",
            new=AsyncMock(return_value=sample_pull),
        ),
        patch(
            "routers.prs.github_service.get_pull_diff",
            new=AsyncMock(return_value=diff),
        ),
        patch(
            "routers.prs.github_service.list_pull_files",
            new=AsyncMock(return_value=files),
        ),
    ):
        response = auth_client.get("/api/prs/tester/demo-repo/7")

    assert response.status_code == 200
    body = response.json()
    assert body["number"] == 7
    assert body["diff"].startswith("diff --git")
    assert len(body["files"]) == 2
    assert body["files"][0]["filename"] == "apps/web/lib/auth/session.ts"
    assert body["additions"] == 12
    assert body["deletions"] == 3


def test_get_pull_rejects_invalid_number(auth_client: TestClient) -> None:
    response = auth_client.get("/api/prs/tester/demo-repo/0")
    assert response.status_code == 400
