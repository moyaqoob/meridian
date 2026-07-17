"""
GitHub OAuth + HttpOnly session cookie.

Locked grill decision: User OAuth token stored encrypted on User.
Session cookie only — no JWTs in client storage.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.helper import (
    OAUTH_STATE_TTL_SECONDS,
    SESSION_COOKIE,
    _redis,
    create_session_token,
    decrypt_access_token,
    encrypt_access_token,
    exchange_github_code,
    get_current_user,
    get_optional_user,
    github_oauth_redirect_uri,
    upsert_user,
)
from models.schemas import SessionOut, UserOut
from models.tables import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

__all__ = [
    "decrypt_access_token",
    "get_current_user",
    "get_optional_user",
    "router",
]


@router.get("/github")
async def github_auth() -> RedirectResponse:
    """Start GitHub OAuth. Stores CSRF state in Redis."""
    state = secrets.token_urlsafe(32)
    _redis().setex(f"oauth_state:{state}", OAUTH_STATE_TTL_SECONDS, "1")

    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "scope": "repo",
            "state": state,
            "redirect_uri": github_oauth_redirect_uri(),
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


async def _handle_github_callback(code: str, state: str, db: Session) -> RedirectResponse:
    """Exchange code, upsert user, set HttpOnly session cookie."""
    redis_client = _redis()
    if not redis_client.get(f"oauth_state:{state}"):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    redis_client.delete(f"oauth_state:{state}")

    access_token, profile = await exchange_github_code(code)
    github_id = profile.get("id")
    login = profile.get("login")
    if not github_id or not login:
        raise HTTPException(status_code=502, detail="GitHub profile missing id/login")

    user = upsert_user(
        db,
        github_id=int(github_id),
        login=str(login),
        encrypted_token=encrypt_access_token(access_token),
    )

    response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/dashboard")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(user.id),
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    return response


@router.get("/callback/github")
async def github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """GitHub OAuth App callback (Authorization callback URL)."""
    return await _handle_github_callback(code, state, db)


@router.get("/callback")
async def github_callback_alias(
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Alias for older callback URL configs."""
    return await _handle_github_callback(code, state, db)


@router.get("/me", response_model=SessionOut)
def auth_me(user: User | None = Depends(get_optional_user)) -> SessionOut:
    """Check whether the session cookie is valid."""
    if user is None:
        return SessionOut(authenticated=False, user=None)
    return SessionOut(
        authenticated=True,
        user=UserOut(id=user.id, github_id=user.github_id, login=user.login),
    )


@router.post("/logout")
def auth_logout(response: Response) -> dict:
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/session", response_model=UserOut)
def require_session(user: User = Depends(get_current_user)) -> UserOut:
    """Protected probe — 401 if not logged in."""
    return UserOut(id=user.id, github_id=user.github_id, login=user.login)
