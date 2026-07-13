"""
GitHub OAuth + HttpOnly session cookie.

Locked grill decision: User OAuth token stored encrypted on User.
Session cookie only — no JWTs in client storage.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

import httpx
import redis
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.schemas import SessionOut, UserOut
from models.tables import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "session"
OAUTH_STATE_TTL_SECONDS = 300


def _session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        settings.session_secret.get_secret_value(),
        salt="meridian-session",
    )


def _fernet() -> Fernet:
    return Fernet(settings.fernet_key.get_secret_value().encode())


def _redis() -> redis.Redis:
    return redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,
    )


def create_session_token(user_id: str) -> str:
    return _session_serializer().dumps({"user_id": user_id})


def read_session_token(token: str) -> str:
    try:
        payload = _session_serializer().loads(
            token,
            max_age=settings.session_max_age_seconds,
        )
    except SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="Session expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    user_id = payload.get("user_id")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(status_code=401, detail="Invalid session payload")
    return user_id


def encrypt_access_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_access_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Failed to decrypt access token") from exc


async def exchange_github_code(code: str) -> tuple[str, dict]:
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret.get_secret_value(),
                "code": code,
            },
        )
        if not token_response.is_success:
            raise HTTPException(status_code=502, detail="GitHub token exchange failed")

        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=token_payload.get("error_description", "No access_token returned"),
            )

        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if not user_response.is_success:
            raise HTTPException(status_code=502, detail="Failed to fetch GitHub user")

        return access_token, user_response.json()


def upsert_user(db: Session, *, github_id: int, login: str, encrypted_token: str) -> User:
    user = db.query(User).filter(User.github_id == github_id).one_or_none()
    if user is None:
        user = User(
            github_id=github_id,
            login=login,
            encrypted_access_token=encrypted_token,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user)
    else:
        user.login = login
        user.encrypted_access_token = encrypted_token

    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = read_session_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        user_id = read_session_token(token)
    except HTTPException:
        return None
    return db.get(User, user_id)


@router.get("/github")
async def github_auth() -> RedirectResponse:
    """Start GitHub OAuth. Stores CSRF state in Redis."""
    state = secrets.token_urlsafe(32)
    _redis().setex(f"oauth_state:{state}", OAUTH_STATE_TTL_SECONDS, "1")

    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&scope=repo"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
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

    response = RedirectResponse(f"{settings.frontend_url}/dashboard")
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
