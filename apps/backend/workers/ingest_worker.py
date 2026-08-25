"""RQ ingest worker — survives API reload (unlike in-process threads)."""

from __future__ import annotations

import logging

from core.database import SessionLocal
from models.tables import Repo
from services.ingestion import ingest_repo_from_github

logger = logging.getLogger(__name__)


def process_ingest(repo_id: str, access_token: str) -> dict | None:
    """
    Clone + chunk + embed a connected repo.
    Status is written to Repo.ingest_status / ingest_error.
    """
    db = SessionLocal()
    try:
        repo = db.get(Repo, repo_id)
        if repo is None:
            logger.warning("ingest aborted: repo not found repo_id=%s", repo_id)
            return None

        logger.info("ingest started repo_id=%s full_name=%s", repo_id, repo.full_name)
        stats = ingest_repo_from_github(repo, access_token, db)
        logger.info(
            "ingest finished repo_id=%s status=%s files=%s",
            repo_id,
            repo.ingest_status,
            repo.files_ingested,
        )
        return stats
    except Exception:
        logger.exception("ingest failed repo_id=%s", repo_id)
        try:
            repo = db.get(Repo, repo_id)
            if repo is not None and repo.ingest_status == "processing":
                repo.ingest_status = "failed"
                if not repo.ingest_error:
                    repo.ingest_error = (
                        "Ingest failed unexpectedly. Check the RQ worker logs and retry."
                    )
                db.commit()
        except Exception:
            db.rollback()
        return None
    finally:
        db.close()
