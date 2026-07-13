"""
Retrieval: embed diff → pgvector cosine similarity → top-k CodeChunk rows.

Retrieval quality is product quality.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.tables import CodeChunk
from services.embedding import embed_single


def build_retrieval_query(diff: str, pr_title: str) -> str:
    """
    Enrich the retrieval query with PR title (intent) + diff (change).
    Improves recall vs embedding the raw unified diff alone.
    """
    title = pr_title.strip()
    if not title:
        return diff
    return f"{title}\n\n{diff}"


async def retrieve_chunks(
    db: Session,
    *,
    repo_id: str,
    diff: str,
    top_k: int = 20,
    pr_title: str = "",
) -> list[CodeChunk]:
    """
    Given a PR diff, return the most relevant indexed chunks for that repo.

    Strategy: embed enriched query → ORDER BY embedding <=> query → LIMIT top_k.
    """
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    query_text = build_retrieval_query(diff, pr_title)
    query_vector = await embed_single(query_text)

    stmt = (
        select(CodeChunk)
        .where(CodeChunk.repo_id == repo_id)
        .order_by(CodeChunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    return list(db.scalars(stmt).all())
