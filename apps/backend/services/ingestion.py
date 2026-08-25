"""
Ingestion: local-path full ingest with checksum upsert.

Locked decisions:
- Progress on Repo (ingest_status + files_ingested)
- Full ingest on connect; incremental on PR merge later
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.tables import CodeChunk, CodeDependency, Repo
from services.chunking import iter_repo_files, parse_file
from services.embedding import embed_batch_sync
from services.imports import collect_repo_file_set, extract_imports


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _replace_dependencies(
    db: Session,
    *,
    repo_id: str,
    root: Path,
    files: list[tuple[Path, str]],
) -> int:
    """Recompute code_dependencies for the repo from the current checkout."""
    repo_files = collect_repo_file_set(files, root)
    db.query(CodeDependency).filter(CodeDependency.repo_id == repo_id).delete(
        synchronize_session=False
    )

    count = 0
    now = _utcnow()
    for file_path, language in files:
        rel = file_path.relative_to(root).as_posix()
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for dep in extract_imports(rel, content, language, repo_files):
            db.add(
                CodeDependency(
                    id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    from_file=dep.from_file,
                    to_file=dep.to_file,
                    edge_type=dep.edge_type,
                    created_at=now,
                )
            )
            count += 1
    return count


def embed_repo_from_path(repo: Repo, repo_path: str, db: Session) -> dict:
    """
    Full ingest from a local checkout.
    Unchanged checksums skipped; orphan checksums removed.
    """
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail=f"repo_path does not exist: {repo_path}")

    tracked = db.get(Repo, repo.id)
    if tracked is None:
        raise HTTPException(status_code=404, detail=f"repo not found: {repo.id}")

    tracked.ingest_status = "processing"
    tracked.ingest_error = None
    db.commit()

    try:
        files = iter_repo_files(root)
        raw_chunks = []
        for file_path, language in files:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            raw_chunks.extend(
                parse_file(content, file_path.relative_to(root).as_posix(), language)
            )

        chunk_by_checksum = {_checksum(c.content): c for c in raw_chunks}
        existing = db.query(CodeChunk).filter(CodeChunk.repo_id == tracked.id).all()
        existing_by_checksum = {row.checksum: row for row in existing}

        new_checksums = set(chunk_by_checksum)
        old_checksums = set(existing_by_checksum)
        to_insert = new_checksums - old_checksums
        to_delete = old_checksums - new_checksums

        if to_delete:
            db.query(CodeChunk).filter(
                CodeChunk.repo_id == tracked.id,
                CodeChunk.checksum.in_(to_delete),
            ).delete(synchronize_session=False)

        new_chunks = [chunk_by_checksum[c] for c in to_insert]
        embeddings = embed_batch_sync([c.content for c in new_chunks])

        for chunk, vector in zip(new_chunks, embeddings):
            db.add(
                CodeChunk(
                    id=str(uuid.uuid4()),
                    repo_id=tracked.id,
                    file_path=chunk.file_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    language=chunk.language,
                    content=chunk.content,
                    checksum=_checksum(chunk.content),
                    embedding=vector,
                )
            )

        deps_written = _replace_dependencies(
            db, repo_id=tracked.id, root=root, files=files
        )

        tracked.files_ingested = len(files)
        tracked.ingest_status = "ready"
        db.commit()

        return {
            "files_ingested": len(files),
            "chunks_total": len(chunk_by_checksum),
            "chunks_inserted": len(to_insert),
            "chunks_removed": len(to_delete),
            "chunks_unchanged": len(new_checksums & old_checksums),
            "dependencies_written": deps_written,
        }
    except Exception as exc:
        tracked.ingest_status = "failed"
        message = str(exc)
        # OpenAI/NVIDIA client errors are huge — keep UI readable.
        if "api_key" in message.lower() or "401" in message or "Unauthorized" in message:
            message = (
                "Embedding API rejected the request (check NVIDIA_API_KEY). "
                f"Detail: {message[:240]}"
            )
        elif len(message) > 500:
            message = message[:500] + "…"
        tracked.ingest_error = message
        db.commit()
        raise


def ingest_repo_from_github(repo: Repo, access_token: str, db: Session) -> dict:
    """
    Clone the GitHub repo shallowly into a temp dir, then run full ingest.
    """
    tracked = db.get(Repo, repo.id)
    if tracked is None:
        raise HTTPException(status_code=404, detail=f"repo not found: {repo.id}")

    tracked.ingest_status = "processing"
    tracked.ingest_error = None
    db.commit()

    tmp_root = Path(tempfile.mkdtemp(prefix="meridian-ingest-"))
    clone_dir = tmp_root / "repo"
    clone_url = f"https://x-access-token:{access_token}@github.com/{tracked.full_name}.git"

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                tracked.default_branch,
                clone_url,
                str(clone_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(clone_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown git error").strip()
            # Don't leak the access token if git echoed the URL.
            err = err.replace(access_token, "***")
            if "Authentication failed" in err or "could not read Username" in err:
                detail = (
                    "GitHub authentication failed while cloning. "
                    "Sign out and sign in again so Meridian gets a fresh repo token."
                )
            elif "not found" in err.lower() or "Repository not found" in err:
                detail = (
                    f"GitHub could not find {tracked.full_name}, or the token "
                    "lacks access. Check the repo still exists and your OAuth "
                    "app has the `repo` scope."
                )
            else:
                detail = f"git clone failed: {err[:500]}"
            raise HTTPException(status_code=502, detail=detail)

        return embed_repo_from_path(tracked, str(clone_dir), db)
    except HTTPException as exc:
        tracked.ingest_status = "failed"
        tracked.ingest_error = str(exc.detail)
        db.commit()
        raise
    except Exception as exc:
        tracked.ingest_status = "failed"
        tracked.ingest_error = str(exc)
        db.commit()
        raise
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
