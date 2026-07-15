"""
Repo management: list connected repos, browse GitHub repos, connect, local embed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.schemas import (
    ConnectRepoRequest,
    EmbedRepoRequest,
    GitHubRepoOut,
    IngestionStatusOut,
    RepoOut,
)
from models.tables import Repo, User
from routers.auth import decrypt_access_token, get_current_user
from services import github as github_service
from services.ingestion import embed_repo_from_path

router = APIRouter(prefix="/api/repos", tags=["repos"])


def _repo_out(repo: Repo) -> RepoOut:
    return RepoOut(
        id=repo.id,
        github_repo_id=repo.github_repo_id,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        ingest_status=repo.ingest_status,  # type: ignore[arg-type]
        files_ingested=repo.files_ingested,
        ingest_error=repo.ingest_error,
    )


@router.get("/", response_model=list[RepoOut])
def list_connected_repos(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RepoOut]:
    """List repos this user has connected to Meridian."""
    rows = (
        db.query(Repo)
        .filter(Repo.user_id == user.id)
        .order_by(Repo.full_name.asc())
        .all()
    )
    return [_repo_out(row) for row in rows]


@router.get("/available", response_model=list[GitHubRepoOut])
async def list_available_github_repos(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GitHubRepoOut]:
    """
    List GitHub repos the user can access, with connected=true if already in Meridian.
    Use this UI to pick a repo to connect.
    """
    token = decrypt_access_token(user.encrypted_access_token)
    remote = await github_service.list_user_repos(token)

    connected_ids = {
        row[0]
        for row in db.query(Repo.github_repo_id).filter(Repo.user_id == user.id).all()
    }

    out: list[GitHubRepoOut] = []
    for item in remote:
        github_id = item.get("id")
        full_name = item.get("full_name")
        if github_id is None or not full_name:
            continue
        out.append(
            GitHubRepoOut(
                github_repo_id=int(github_id),
                full_name=str(full_name),
                default_branch=str(item.get("default_branch") or "main"),
                private=bool(item.get("private")),
                connected=int(github_id) in connected_ids,
            )
        )
    return out


@router.post("/connect", response_model=RepoOut)
async def connect_repo(
    body: ConnectRepoRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepoOut:
    """
    Connect a GitHub repo to Meridian (single owner for v1).
    Creates a Repo row with ingest_status=pending.
    Indexing: call POST /api/repos/embed with a local checkout path for now.
    """
    full_name = body.full_name.strip()
    if "/" not in full_name or full_name.count("/") != 1:
        raise HTTPException(status_code=400, detail="full_name must be owner/repo")

    token = decrypt_access_token(user.encrypted_access_token)
    remote = await github_service.get_repo(token, full_name)

    github_repo_id = int(remote["id"])
    default_branch = str(remote.get("default_branch") or "main")

    existing = (
        db.query(Repo)
        .filter(Repo.github_repo_id == github_repo_id)
        .one_or_none()
    )
    if existing is not None:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=409,
                detail="Repo already connected by another Meridian user",
            )
        return _repo_out(existing)

    repo = Repo(
        user_id=user.id,
        github_repo_id=github_repo_id,
        full_name=full_name,
        default_branch=default_branch,
        ingest_status="pending",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return _repo_out(repo)


@router.get("/{repo_id}/ingest", response_model=IngestionStatusOut)
def get_ingest_status(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestionStatusOut:
    """Poll ingest status for a connected repo."""
    repo = db.get(Repo, repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")
    return IngestionStatusOut(
        repo_id=repo.id,
        status=repo.ingest_status,  # type: ignore[arg-type]
        files_ingested=repo.files_ingested,
        error_message=repo.ingest_error,
    )


@router.post("/embed")
def embed_local_repo(
    body: EmbedRepoRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run full local-path ingest (tree-sitter → embed → checksum upsert).
    Temporary until GitHub-backed clone ingest is wired.
    """
    repo = db.get(Repo, body.repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")

    stats = embed_repo_from_path(repo, body.repo_path, db)
    return {"status": "ok", "repo_id": body.repo_id, **stats}
