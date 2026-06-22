import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from tree_sitter import Language, Parser

from models.tables import Base, CodeChunk, Repo

router = APIRouter(prefix="/api/repos", tags=["repos"])

SKIP_DIRS = {"node_modules", "vendor", ".git", "dist", "build", "__pycache__", ".venv"}
SKIP_EXTENSIONS = {".lock", ".sum", ".mod", ".min.js", ".min.css"}
SUPPORTED_LANGUAGES = {"python", "typescript", "javascript"}
EXT_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}
TARGET_NODE_TYPES = {
    "python": {"function_definition", "class_definition", "decorated_definition"},
    "typescript": {"function_declaration", "method_definition", "class_declaration"},
    "javascript": {"function_declaration", "method_definition", "class_declaration"},
}

_parsers: dict[str, Parser] = {}


@dataclass
class RawChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str


class EmbedRepoRequest(BaseModel):
    repo_id: str
    repo_path: str


def _get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not set")
    return database_url


def _get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _get_session() -> Session:
    engine = create_engine(_get_database_url())
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _get_parser(language: str) -> Parser | None:
    if language in _parsers:
        return _parsers[language]

    try:
        if language == "python":
            import tree_sitter_python as lang_mod
        elif language == "typescript":
            import tree_sitter_typescript as lang_mod
        elif language == "javascript":
            import tree_sitter_javascript as lang_mod
        else:
            return None

        parser = Parser(Language(lang_mod.language()))
        _parsers[language] = parser
        return parser
    except Exception:
        return None


def should_index_file(path: str, language: str) -> bool:
    parts = Path(path).parts
    if any(part in SKIP_DIRS for part in parts):
        return False
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    if language not in SUPPORTED_LANGUAGES:
        return False
    return True


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sliding_window_chunks(content: str, file_path: str, language: str) -> list[RawChunk]:
    lines = content.splitlines()
    window = 50
    overlap = 10
    chunks: list[RawChunk] = []

    for start in range(0, len(lines), max(window - overlap, 1)):
        block = "\n".join(lines[start : start + window])
        if len(block.strip()) < 20:
            continue
        chunks.append(
            RawChunk(
                content=block,
                file_path=file_path,
                start_line=start + 1,
                end_line=min(start + window, len(lines)),
                language=language,
            )
        )

    return chunks


def _walk_meaningful_nodes(node, language: str):
    targets = TARGET_NODE_TYPES.get(language, set())
    if node.type in targets:
        yield node
        return

    for child in node.children:
        yield from _walk_meaningful_nodes(child, language)


def parse_file(content: str, file_path: str, language: str) -> list[RawChunk]:
    parser = _get_parser(language)
    if parser is None:
        return _sliding_window_chunks(content, file_path, language)

    tree = parser.parse(content.encode("utf-8"))
    chunks: list[RawChunk] = []

    for node in _walk_meaningful_nodes(tree.root_node, language):
        chunk_text = content[node.start_byte : node.end_byte]
        if len(chunk_text.strip()) < 20:
            continue
        chunks.append(
            RawChunk(
                content=chunk_text,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language,
            )
        )

    if not chunks:
        return _sliding_window_chunks(content, file_path, language)

    return chunks


def _iter_repo_files(repo_path: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []

    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue

        rel_path = path.relative_to(repo_path).as_posix()
        language = EXT_TO_LANGUAGE.get(path.suffix.lower())
        if not language:
            continue
        if not should_index_file(rel_path, language):
            continue

        files.append((path, language))

    return files


def _embed_batch(client: OpenAI, texts: list[str], batch_size: int = 100) -> list[list[float]]:
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        embeddings.extend(item.embedding for item in response.data)

    return embeddings


def embed_repo(repository: Repo, repo_path: str, session: Session) -> int:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail=f"repo_path does not exist: {repo_path}")

    repo = session.get(Repo, repository.id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo not found: {repository.id}")

    repo.ingest_status = "processing"
    session.commit()

    raw_chunks: list[RawChunk] = []
    for file_path, language in _iter_repo_files(root):
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        raw_chunks.extend(parse_file(content, file_path.relative_to(root).as_posix(), language))

    client = _get_openai_client()
    embeddings = _embed_batch(client, [chunk.content for chunk in raw_chunks])

    session.query(CodeChunk).filter(CodeChunk.repo_id == repo.id).delete()

    for chunk, vector in zip(raw_chunks, embeddings):
        session.add(
            CodeChunk(
                id=str(uuid.uuid4()),
                repo_id=repo.id,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                language=chunk.language,
                content=chunk.content,
                checksum=_checksum(chunk.content),
                embedding=vector,
            )
        )

    repo.ingest_status = "ready"
    session.commit()
    return len(raw_chunks)


@router.post("/embed")
def embed_repo_endpoint(body: EmbedRepoRequest) -> dict:
    session = _get_session()
    try:
        repository = session.get(Repo, body.repo_id)
        if repository is None:
            raise HTTPException(status_code=404, detail=f"repo not found: {body.repo_id}")

        chunks_embedded = embed_repo(repository, body.repo_path, session)
        return {
            "status": "ok",
            "repo_id": body.repo_id,
            "chunks_embedded": chunks_embedded,
        }
    finally:
        session.close()
