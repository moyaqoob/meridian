from typing import List

from apps.backend.models.tables import CodeChunk  # adjust import if package root changes


async def ingest_repo(repo_id: str, installation_id: str, full_name: str) -> None:
    """
    Full ingestion pipeline for a connected repository.
    Designed to be idempotent — safe to re-run on the same repo.
    Unchanged files (same sha) are skipped via checksum dedup.
    """
    # The concrete GitHub, chunking, and embedding services will live alongside this
    # module and be wired in once they are implemented.
    from apps.backend.services import github, chunking, embedding  # local import to avoid cycles

    # 1. Fetch file tree from GitHub API
    files = await github.get_file_tree(installation_id, full_name)

    # 2. Filter — skip vendor, test, generated, binary
    files = [f for f in files if should_index_file(f.path, getattr(f, "language", ""))]

    # 3. Chunk each file using tree-sitter
    chunks: List[CodeChunk] = []
    for file in files:
        content = await github.get_file_content(installation_id, full_name, file.path)
        file_chunks = chunking.parse_file(content, file.path, getattr(file, "language", ""))
        chunks.extend(file_chunks)

    # 4. Deduplicate — skip chunks whose checksum already exists in DB for this repo
    new_chunks = dedup_by_checksum(repo_id, chunks)

    # 5. Embed in batches of 100 — never one at a time
    embeddings = await embedding.embed_batch(
        texts=[c.content for c in new_chunks],
        batch_size=100,
    )

    # 6. Upsert into code_chunks
    for chunk, vector in zip(new_chunks, embeddings):
        upsert_chunk(repo_id=repo_id, chunk=chunk, embedding=vector)

    # 7. Mark repo ready
    update_repo_status(repo_id, "ready")


def should_index_file(path: str, language: str) -> bool:
    """
    Conservative filter. When in doubt, skip.
    We want signal-dense chunks, not noise-dense chunks.
    """
    SKIP_DIRS = {"node_modules", "vendor", ".git", "dist", "build", "__pycache__"}
    SKIP_EXTENSIONS = {".lock", ".sum", ".mod", ".min.js", ".min.css"}
    SUPPORTED_LANGUAGES = {"python", "typescript", "javascript", "go", "java", "rust"}

    parts = path.split("/")
    if any(part in SKIP_DIRS for part in parts):
        return False
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    if language not in SUPPORTED_LANGUAGES:
        return False
    return True


def dedup_by_checksum(repo_id: str, chunks: List[CodeChunk]) -> List[CodeChunk]:
    """
    Placeholder for checksum-based deduplication.
    Replace with a real implementation that queries the database for existing checksums.
    """
    return chunks


def upsert_chunk(repo_id: str, chunk: CodeChunk, embedding: List[float]) -> None:
    """
    Placeholder for upserting a chunk + embedding into the database.
    Implement using your SQLAlchemy session and pgvector mapping.
    """
    raise NotImplementedError("upsert_chunk must be implemented against the database layer.")


def update_repo_status(repo_id: str, status: str) -> None:
    """
    Placeholder for updating a repo's ingest_status.
    Implement using your SQLAlchemy session.
    """
    raise NotImplementedError("update_repo_status must be implemented against the database layer.")

