"""
Ingestion: local-path full ingest with checksum upsert.

Locked decisions:
- Progress on Repo (ingest_status + files_ingested)
- Full ingest on connect; incremental on PR merge later
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.tables import CodeChunk, Repo
from services.chunking import iter_repo_files, parse_file
from services.embedding import embed_batch_sync


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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

        tracked.files_ingested = len(files)
        tracked.ingest_status = "ready"
        db.commit()

        return {
            "files_ingested": len(files),
            "chunks_total": len(chunk_by_checksum),
            "chunks_inserted": len(to_insert),
            "chunks_removed": len(to_delete),
            "chunks_unchanged": len(new_checksums & old_checksums),
        }
    except Exception as exc:
        tracked.ingest_status = "failed"
        tracked.ingest_error = str(exc)
        db.commit()
        raise
