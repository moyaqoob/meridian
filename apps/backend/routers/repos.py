"""
Repo management: list connected repos, browse GitHub repos, connect, ingest.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from core.database import get_db
from models.schemas import (
    ConnectRepoRequest,
    EmbedRepoRequest,
    FileChunkOut,
    GitHubRepoOut,
    GraphEdgeOut,
    GraphNodeOut,
    GraphOut,
    IngestionStatusOut,
    RepoOut,
)
from models.tables import CodeChunk, CodeDependency, Repo, User
from routers.auth import decrypt_access_token, get_current_user
from services import github as github_service
from services.imports import language_for_path
from services.ingestion import embed_repo_from_path
from services.job_queue import enqueue_ingest_job

router = APIRouter(prefix="/api/repos", tags=["repos"])
logger = logging.getLogger(__name__)


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
    List GitHub repos the user can access, with connected/ingest state if in Meridian.
    """
    token = decrypt_access_token(user.encrypted_access_token)
    remote = await github_service.list_user_repos(token)

    connected = {
        row.github_repo_id: row
        for row in db.query(Repo).filter(Repo.user_id == user.id).all()
    }

    out: list[GitHubRepoOut] = []
    for item in remote:
        github_id = item.get("id")
        full_name = item.get("full_name")
        if github_id is None or not full_name:
            continue
        row = connected.get(int(github_id))
        out.append(
            GitHubRepoOut(
                github_repo_id=int(github_id),
                full_name=str(full_name),
                default_branch=str(item.get("default_branch") or "main"),
                private=bool(item.get("private")),
                connected=row is not None,
                repo_id=row.id if row is not None else None,
                ingest_status=row.ingest_status if row is not None else None,  # type: ignore[arg-type]
                files_ingested=row.files_ingested if row is not None else None,
                ingest_error=row.ingest_error if row is not None else None,
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


@router.post("/{repo_id}/ingest", response_model=IngestionStatusOut)
async def start_ingest(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestionStatusOut:
    """
    Enqueue GitHub clone + embed ingest on the RQ worker.
    Poll GET /api/repos/{repo_id}/ingest for status.
    """
    repo = db.get(Repo, repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")

    token = decrypt_access_token(user.encrypted_access_token)

    try:
        outcome = enqueue_ingest_job(repo_id=repo.id, access_token=token)
    except (RedisError, ConnectionError, OSError) as exc:
        logger.exception("failed to enqueue ingest repo_id=%s", repo_id)
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot reach Redis / RQ. Start Docker Redis and run: "
                "`uv run rq worker meridian-ingest meridian-reviews`"
            ),
        ) from exc

    if outcome == "already_running":
        # Keep DB status aligned with the live RQ job.
        if repo.ingest_status != "processing":
            repo.ingest_status = "processing"
            db.commit()
        return IngestionStatusOut(
            repo_id=repo.id,
            status="processing",
            files_ingested=repo.files_ingested,
            error_message=repo.ingest_error,
        )

    repo.ingest_status = "processing"
    repo.ingest_error = None
    db.commit()

    return IngestionStatusOut(
        repo_id=repo.id,
        status="processing",
        files_ingested=repo.files_ingested,
        error_message=None,
    )


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


@router.get("/{repo_id}/graph", response_model=GraphOut)
def get_repo_graph(
    repo_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GraphOut:
    """Return the file-level import/dependency graph built during ingestion."""
    repo = db.get(Repo, repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")

    chunks = db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).all()
    deps = db.query(CodeDependency).filter(CodeDependency.repo_id == repo_id).all()

    stats: dict[str, dict] = {}
    for chunk in chunks:
        entry = stats.setdefault(
            chunk.file_path,
            {"language": chunk.language, "loc": 0, "chunk_count": 0, "external_deps": 0},
        )
        entry["chunk_count"] += 1
        entry["loc"] = max(entry["loc"], int(chunk.end_line or 0))

    for dep in deps:
        if dep.from_file not in stats:
            stats[dep.from_file] = {
                "language": language_for_path(dep.from_file),
                "loc": 0,
                "chunk_count": 0,
                "external_deps": 0,
            }
        if dep.edge_type == "external":
            stats[dep.from_file]["external_deps"] += 1
        elif dep.to_file:
            if dep.to_file not in stats:
                stats[dep.to_file] = {
                    "language": language_for_path(dep.to_file),
                    "loc": 0,
                    "chunk_count": 0,
                    "external_deps": 0,
                }

    nodes = [
        GraphNodeOut(
            id=path,
            language=meta["language"],
            loc=int(meta["loc"]),
            chunk_count=int(meta["chunk_count"]),
            external_deps=int(meta["external_deps"]),
        )
        for path, meta in sorted(stats.items())
    ]

    edges: list[GraphEdgeOut] = []
    seen: set[tuple[str, str, str]] = set()
    for dep in deps:
        if dep.edge_type == "external" or not dep.to_file:
            continue
        edge_type = "reexport" if dep.edge_type == "reexport" else "import"
        key = (dep.from_file, dep.to_file, edge_type)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            GraphEdgeOut(source=dep.from_file, target=dep.to_file, type=edge_type)
        )

    return GraphOut(nodes=nodes, edges=edges)


@router.get("/{repo_id}/chunks", response_model=list[FileChunkOut])
def get_file_chunks(
    repo_id: str,
    file_path: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FileChunkOut]:
    """List indexed chunks for a single file (graph node drill-down)."""
    repo = db.get(Repo, repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")
    if not file_path.strip():
        raise HTTPException(status_code=400, detail="file_path is required")

    rows = (
        db.query(CodeChunk)
        .filter(CodeChunk.repo_id == repo_id, CodeChunk.file_path == file_path)
        .order_by(CodeChunk.start_line.asc())
        .all()
    )
    return [
        FileChunkOut(
            id=row.id,
            file_path=row.file_path,
            start_line=row.start_line,
            end_line=row.end_line,
            language=row.language,
            content=row.content,
        )
        for row in rows
    ]


@router.post("/embed")
def embed_local_repo(
    body: EmbedRepoRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run full local-path ingest (tree-sitter → embed → checksum upsert).
    Temporary until GitHub-backed clone ingest is preferred.
    """
    repo = db.get(Repo, body.repo_id)
    if repo is None or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repo not found")

    stats = embed_repo_from_path(repo, body.repo_path, db)
    return {"status": "ok", "repo_id": body.repo_id, **stats}
