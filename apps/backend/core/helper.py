from __future__ import annotations

from datetime import datetime, timezone

import httpx
import redis
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.tables import User

SESSION_COOKIE = "session"
OAUTH_STATE_TTL_SECONDS = 300


def _session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        settings.session_secret.get_secret_value(),
        salt="meridian-session",
    )


def _fernet() -> Fernet:
    """Fernet encryptor for GitHub OAuth tokens stored on User.encrypted_access_token."""
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
    """Encrypt a GitHub access token before persisting to the database."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_access_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Failed to decrypt access token") from exc


def github_oauth_redirect_uri() -> str:
    """Must match the GitHub OAuth App callback URL (via Next.js /api rewrite)."""
    return f"{settings.frontend_url.rstrip('/')}/api/auth/callback/github"


async def exchange_github_code(code: str) -> tuple[str, dict]:
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": github_oauth_redirect_uri(),
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
