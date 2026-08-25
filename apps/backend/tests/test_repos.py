"""Repo route tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from models.tables import Repo, User


def test_list_connected_repos_requires_auth(client: TestClient) -> None:
    response = client.get("/api/repos/")
    assert response.status_code == 401


def test_list_connected_repos_empty(auth_client: TestClient, mock_db: MagicMock) -> None:
    mock_db.all.return_value = []
    response = auth_client.get("/api/repos/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_connected_repos_returns_rows(
    auth_client: TestClient,
    mock_db: MagicMock,
    test_user: User,
) -> None:
    repo = Repo(
        id="repo-1",
        user_id=test_user.id,
        github_repo_id=1001,
        full_name="tester/demo-repo",
        default_branch="main",
        ingest_status="pending",
        files_ingested=None,
        ingest_error=None,
    )
    mock_db.all.return_value = [repo]

    response = auth_client.get("/api/repos/")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["full_name"] == "tester/demo-repo"
    assert body[0]["ingest_status"] == "pending"


def test_available_repos_marks_connected(
    auth_client: TestClient,
    mock_db: MagicMock,
    sample_github_repo: dict[str, Any],
    test_user: User,
) -> None:
    connected = Repo(
        id="repo-1",
        user_id=test_user.id,
        github_repo_id=1001,
        full_name="tester/demo-repo",
        default_branch="main",
        ingest_status="ready",
        files_ingested=42,
        ingest_error=None,
    )
    mock_db.all.return_value = [connected]

    with patch(
        "routers.repos.github_service.list_user_repos",
        return_value=[
            sample_github_repo,
            {
                "id": 2002,
                "full_name": "tester/other",
                "default_branch": "main",
                "private": False,
            },
        ],
    ):
        response = auth_client.get("/api/repos/available")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    by_id = {row["github_repo_id"]: row for row in body}
    assert by_id[1001]["connected"] is True
    assert by_id[1001]["ingest_status"] == "ready"
    assert by_id[1001]["repo_id"] == "repo-1"
    assert by_id[2002]["connected"] is False
    assert by_id[2002]["ingest_status"] is None
    assert by_id[1001]["full_name"] == "tester/demo-repo"


def test_connect_repo_creates_row(
    auth_client: TestClient,
    mock_db: MagicMock,
    sample_github_repo: dict[str, Any],
    test_user: User,
) -> None:
    mock_db.one_or_none.return_value = None

    created: dict[str, Any] = {}

    def _add(obj: Any) -> None:
        created["repo"] = obj
        obj.id = "repo-new"
        obj.ingest_status = "pending"
        obj.files_ingested = None
        obj.ingest_error = None

    mock_db.add.side_effect = _add
    mock_db.refresh.side_effect = lambda obj: None

    with patch(
        "routers.repos.github_service.get_repo",
        return_value=sample_github_repo,
    ):
        response = auth_client.post(
            "/api/repos/connect",
            json={"full_name": "tester/demo-repo"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "tester/demo-repo"
    assert body["github_repo_id"] == 1001
    assert body["ingest_status"] == "pending"
    assert "repo" in created
    assert created["repo"].user_id == test_user.id
    mock_db.commit.assert_called()


def test_connect_repo_rejects_bad_name(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/repos/connect",
        json={"full_name": "not-a-repo"},
    )
    assert response.status_code == 400


def test_ingest_status_not_found(auth_client: TestClient, mock_db: MagicMock) -> None:
    mock_db.get.return_value = None
    response = auth_client.get("/api/repos/missing/ingest")
    assert response.status_code == 404
