"""
Shared fixtures for API route tests.

Env is set before any app imports so Settings / Fernet keys resolve.
DB and GitHub are mocked — these tests do not require a running Postgres.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from cryptography.fernet import Fernet

# Must run before importing core.config / main.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/meridian_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-github-client-id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-github-client-secret")
os.environ.setdefault("NVIDIA_API_KEY", "test-nvidia-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("SESSION_SECRET", "test-session-secret-value-32chars!!")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.database import get_db
from core.helper import encrypt_access_token, get_current_user, get_optional_user
from models.tables import User
from routers.auth import router as auth_router
from routers.prs import router as prs_router
from routers.repos import router as repos_router
from routers.webhook import router as webhook_router


@pytest.fixture
def test_user() -> User:
    return User(
        id="user-test-1",
        github_id=4242,
        login="tester",
        encrypted_access_token=encrypt_access_token("gho_test_access_token"),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.order_by.return_value = db
    db.all.return_value = []
    db.one_or_none.return_value = None
    db.get.return_value = None
    return db


@pytest.fixture
def app(mock_db: MagicMock) -> FastAPI:
    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(repos_router)
    application.include_router(prs_router)
    application.include_router(webhook_router)

    def _override_db():
        yield mock_db

    application.dependency_overrides[get_db] = _override_db
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(app: FastAPI, test_user: User, mock_db: MagicMock) -> TestClient:
    """Client with an authenticated user wired through dependency overrides."""
    mock_db.get.return_value = test_user

    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_optional_user] = lambda: test_user

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_github_repo() -> dict[str, Any]:
    return {
        "id": 1001,
        "full_name": "tester/demo-repo",
        "default_branch": "main",
        "private": True,
    }


@pytest.fixture
def sample_pull() -> dict[str, Any]:
    return {
        "number": 7,
        "title": "Add session hardening",
        "state": "open",
        "user": {"login": "tester"},
        "html_url": "https://github.com/tester/demo-repo/pull/7",
        "updated_at": "2026-07-15T12:00:00Z",
        "base": {"ref": "main"},
        "head": {"ref": "feat/auth"},
        "additions": 12,
        "deletions": 3,
        "changed_files": 2,
        "body": "Hardens cookie handling.",
    }
