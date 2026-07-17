"""Auth route tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from models.tables import User


def test_auth_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


def test_auth_me_authenticated(auth_client: TestClient, test_user: User) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["id"] == test_user.id
    assert body["user"]["login"] == "tester"
    assert body["user"]["github_id"] == 4242


def test_auth_session_requires_login(client: TestClient) -> None:
    response = client.get("/api/auth/session")
    assert response.status_code == 401


def test_auth_session_ok(auth_client: TestClient, test_user: User) -> None:
    response = auth_client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["login"] == test_user.login


def test_auth_logout_clears_cookie(client: TestClient) -> None:
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # Set-Cookie should clear the session cookie
    set_cookie = response.headers.get("set-cookie", "")
    assert "session=" in set_cookie.lower() or "session" in set_cookie.lower()


def test_github_oauth_start_redirects(client: TestClient) -> None:
    fake_redis = MagicMock()
    with patch("routers.auth._redis", return_value=fake_redis):
        response = client.get("/api/auth/github", follow_redirects=False)

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=test-github-client-id" in location
    assert "scope=repo" in location
    assert "state=" in location
    assert "redirect_uri=" in location
    assert "api%2Fauth%2Fcallback%2Fgithub" in location
    fake_redis.setex.assert_called_once()


def test_github_callback_rejects_bad_state(client: TestClient) -> None:
    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with patch("routers.auth._redis", return_value=fake_redis):
        response = client.get(
            "/api/auth/callback/github",
            params={"code": "abc", "state": "bad"},
            follow_redirects=False,
        )
    assert response.status_code == 400


def test_github_callback_alias_rejects_bad_state(client: TestClient) -> None:
    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with patch("routers.auth._redis", return_value=fake_redis):
        response = client.get(
            "/api/auth/callback",
            params={"code": "abc", "state": "bad"},
            follow_redirects=False,
        )
    assert response.status_code == 400
