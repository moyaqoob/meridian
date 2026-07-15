---
description: Backend rules
alwaysApply: true
---

# Meridian — Backend Rules
# Python · FastAPI · PostgreSQL + pgvector · Redis · RQ

---

## What This Backend Is

The Meridian backend is a **retrieval pipeline with an HTTP interface**.
It is not a CRUD API. The API is thin. The real work happens in workers.

Two things this backend does:

1. **Index a repository** — walk, parse, chunk, embed, store
2. **Review a pull request** — fetch diff, retrieve context, generate review, stream results

Every design decision traces back to one of those two pipelines.
If a new piece of code doesn't clearly serve one of them, question whether it belongs.

---

## Project Structure

```
backend/
  app/
    main.py                   # FastAPI app init, middleware, router registration
    config.py                 # Pydantic Settings — all config from env vars
    deps.py                   # FastAPI dependencies: DB session, auth, rate limit

    routers/
      auth.py                 # GitHub OAuth — /api/auth/github, /api/auth/callback
      repos.py                # Repo management — connect, list, ingest trigger
      review.py               # Review endpoints — trigger, SSE stream
      webhooks.py             # GitHub webhook receiver — verify, dedupe, enqueue

    services/
      github.py               # All GitHub API calls — diffs, file trees, OAuth
      ingestion.py            # Orchestrates: clone → parse → chunk → embed → store
      chunking.py             # tree-sitter parsing → CodeChunk list
      embedding.py            # Batch embedding via OpenAI API
      retrieval.py            # Embed diff → pgvector similarity → top-k chunks
      review_gen.py           # Prompt assembly → Claude streaming → ReviewOut
      pipeline_events.py      # SSE event construction + emission

    workers/
      ingest_worker.py        # RQ job: runs ingestion pipeline for a repo
      review_worker.py        # RQ job: runs review pipeline for a PR

    models/
      tables.py               # SQLAlchemy ORM table definitions
      schemas.py              # Pydantic request/response/internal schemas

    middleware/
      auth.py                 # Session cookie validation
      rate_limit.py           # Per-user sliding window via Redis
      logging.py              # structlog JSON request logging

  tests/
    unit/
    integration/
  scripts/
    migrate.py                # Alembic migration runner
    seed.py                   # Dev seed data
  Dockerfile
  pyproject.toml
  alembic.ini
```

---

## Configuration

**All configuration comes from environment variables. Nothing is hardcoded.**

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str

    # GitHub App
    github_app_id: str
    github_app_private_key: str
    github_webhook_secret: str
    github_client_id: str
    github_client_secret: str

    # AI
    openai_api_key: str
    anthropic_api_key: str

    # Security
    fernet_key: str           # for encrypting GitHub access tokens at rest
    session_secret: str

    # App
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Never import `os.environ` directly anywhere in the codebase.**
All config flows through `settings`. This makes the config surface auditable.

---

## Database — SQLAlchemy + pgvector

**All table definitions in one file.**

```python
# app/models/tables.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id = Column(Integer, unique=True, nullable=False)
    login = Column(String, nullable=False)
    encrypted_access_token = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    repos = relationship("Repo", back_populates="user")

class Repo(Base):
    __tablename__ = "repos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    github_repo_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=False)       # "owner/repo"
    default_branch = Column(String, nullable=False)
    ingest_status = Column(
        Enum("pending", "processing", "ready", "failed", name="ingest_status_enum"),
        nullable=False,
        default="pending"
    )

class CodeChunk(Base):
    __tablename__ = "code_chunks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    file_path = Column(String, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    language = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    checksum = Column(String, nullable=False)
    embedding = Column(Vector(1536), nullable=False)

class PR(Base):
    __tablename__ = "prs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    github_pr_id = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    head_sha = Column(String, nullable=False)
    base_sha = Column(String, nullable=False)
    status = Column(
        Enum("pending", "running", "reviewed", "failed", name="pr_status_enum"),
        nullable=False,
        default="pending"
    )

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_id = Column(String, ForeignKey("prs.id"), nullable=False)
    summary = Column(Text, nullable=False)
    structured_json = Column(Text, nullable=False)   # full ReviewOut as JSON string
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    annotations = relationship("ReviewAnnotation", back_populates="review")

class ReviewAnnotation(Base):
    __tablename__ = "review_annotations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String, ForeignKey("reviews.id"), nullable=False)
    file_path = Column(String, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)
    severity = Column(
        Enum("high", "medium", "low", name="severity_enum"),
        nullable=False
    )
    category = Column(String, nullable=False)        # "performance", "security", etc.

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    status = Column(
        Enum("pending", "running", "complete", "failed", name="job_status_enum"),
        nullable=False,
        default="pending"
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    files_ingested = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

# v2 — create now, wire up later
class AcceptedPR(Base):
    __tablename__ = "accepted_prs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    diff = Column(Text, nullable=False)
    review_summary = Column(Text, nullable=False)
    merged_at = Column(DateTime, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # nullable until v2 wires it up
```

**pgvector index on code_chunks.**
Without this, every similarity search is a full table scan.

```sql
-- In your Alembic migration:
CREATE INDEX ON code_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## Schemas — Pydantic

**Separate schemas for request, response, and internal use.**
Never expose ORM objects directly to the API layer.

```python
# app/models/schemas.py

# --- Review ---

class ReviewFinding(BaseModel):
    id: str
    severity: Literal["high", "medium", "low"]
    category: str
    title: str
    comment: str
    file_path: str | None = None
    chunk_ref: str | None = None    # "[CHUNK_ID: N]" reference from LLM

class ReviewOut(BaseModel):
    review_id: str
    pr_id: str
    summary: str
    pr_type: Literal["feat", "fix", "refactor", "chore"]
    findings: list[ReviewFinding]
    model_version: str
    timings: dict[str, float]       # stage -> duration_ms

# --- SSE Events ---

class StageUpdateEvent(BaseModel):
    stage: Literal["validation", "retrieval", "generation", "citation-mapping", "complete"]
    progress: float                 # 0.0 to 1.0
    message: str
    duration_ms: float | None = None

class GenerationChunkEvent(BaseModel):
    text: str
    phase: Literal["summary", "findings"]

class CompleteEvent(BaseModel):
    review_id: str
    status: Literal["complete"]
    summary: str
    findings: list[ReviewFinding]
    timings: dict[str, float]

class ErrorEvent(BaseModel):
    stage: str
    message: str
    retryable: bool

# --- Ingestion ---

class IngestionStatusOut(BaseModel):
    job_id: str
    status: Literal["pending", "running", "complete", "failed"]
    files_ingested: int | None = None
    current_step: str | None = None
    progress: float | None = None   # 0.0 to 1.0
    error_message: str | None = None
```

---

## Webhook Handler

**The most critical rule in the entire backend: return 200 immediately.**

```python
# app/routers/webhooks.py

@router.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    # 1. Verify HMAC signature — reject immediately if invalid
    body = await request.body()
    verify_github_signature(body, request.headers.get("X-Hub-Signature-256"))

    payload = json.loads(body)
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    # 2. Only handle pull_request events with action=opened or action=synchronize
    if event_type != "pull_request":
        return {"status": "ignored"}

    if payload["action"] not in ("opened", "synchronize"):
        return {"status": "ignored"}

    # 3. Deduplicate — if we've seen this delivery ID, ignore it
    if not redis_client.set(f"webhook:{delivery_id}", "1", nx=True, ex=86400):
        return {"status": "duplicate"}

    # 4. Enqueue the job — this is instantaneous
    background_tasks.add_task(
        enqueue_review_job,
        installation_id=payload["installation"]["id"],
        repo_full_name=payload["repository"]["full_name"],
        pr_number=payload["pull_request"]["number"],
        head_sha=payload["pull_request"]["head"]["sha"],
    )

    # 5. Return immediately — never do real work here
    return {"status": "accepted"}
```

**HMAC verification is non-negotiable. Fail fast if it's wrong.**

```python
def verify_github_signature(body: bytes, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing signature")

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")
```

---

## Workers — RQ

**Workers are the real backend. The API is just the interface.**

```python
# app/workers/review_worker.py

import structlog
from app.services.github import fetch_pr_diff
from app.services.retrieval import retrieve_chunks
from app.services.review_gen import generate_review
from app.services.pipeline_events import emit_stage

log = structlog.get_logger()

def run_review(
    pr_id: str,
    repo_id: str,
    pr_number: int,
    head_sha: str,
    installation_id: str,
):
    log = log.bind(pr_id=pr_id, repo_id=repo_id, pr_number=pr_number)

    try:
        # STAGE: validation
        emit_stage(pr_id, stage="validation", progress=0.0, message="Validating PR...")
        diff = fetch_pr_diff(installation_id, repo_id, pr_number)
        emit_stage(pr_id, stage="validation", progress=1.0, message="PR validated")

        # STAGE: retrieval
        emit_stage(pr_id, stage="retrieval", progress=0.0, message="Retrieving context...")
        chunks = retrieve_chunks(repo_id=repo_id, diff=diff, top_k=20)
        emit_stage(pr_id, stage="retrieval", progress=1.0,
                   message=f"Retrieved {len(chunks)} relevant chunks")

        # STAGE: generation
        emit_stage(pr_id, stage="generation", progress=0.0, message="Generating review...")
        review = generate_review(pr_id=pr_id, diff=diff, chunks=chunks)
        emit_stage(pr_id, stage="generation", progress=1.0, message="Review complete")

        # STAGE: complete
        store_review(pr_id=pr_id, review=review)
        emit_complete(pr_id=pr_id, review=review)

    except Exception as e:
        log.error("review_job_failed", error=str(e))
        emit_error(pr_id=pr_id, stage="unknown", message=str(e), retryable=True)
        raise   # re-raise so RQ marks the job as failed
```

**Workers log everything with structured context.**

Every log line in a worker must carry: `pr_id`, `repo_id`, `stage`, `duration_ms`.
When a review fails at 2 AM, you must be able to reconstruct exactly what happened.

---

## Ingestion Service

**The ingestion pipeline is the foundation. Get it right.**

```python
# app/services/ingestion.py

async def ingest_repo(repo_id: str, installation_id: str, full_name: str) -> None:
    """
    Full ingestion pipeline for a connected repository.
    Designed to be idempotent — safe to re-run on the same repo.
    Unchanged files (same sha) are skipped via checksum dedup.
    """

    # 1. Fetch file tree from GitHub API
    files = await github.get_file_tree(installation_id, full_name)

    # 2. Filter — skip vendor, test, generated, binary
    files = [f for f in files if should_index_file(f.path, f.language)]

    # 3. Chunk each file using tree-sitter
    chunks: list[CodeChunk] = []
    for file in files:
        content = await github.get_file_content(installation_id, full_name, file.path)
        file_chunks = chunking.parse_file(content, file.path, file.language)
        chunks.extend(file_chunks)

    # 4. Deduplicate — skip chunks whose checksum already exists in DB for this repo
    new_chunks = dedup_by_checksum(repo_id, chunks)

    # 5. Embed in batches of 100 — never one at a time
    embeddings = await embedding.embed_batch(
        texts=[c.content for c in new_chunks],
        batch_size=100
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
```

---

## Chunking Service — tree-sitter

**Chunk at semantic boundaries. Never by character count.**

```python
# app/services/chunking.py

from tree_sitter import Language, Parser
from dataclasses import dataclass

@dataclass
class RawChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    node_type: str       # "function", "class", "method", "module"
    name: str | None     # function name, class name, etc.

def parse_file(content: str, file_path: str, language: str) -> list[RawChunk]:
    """
    Parse a file using tree-sitter and extract meaningful code units.
    Falls back to sliding-window chunking if language is not supported.
    """
    parser = get_parser(language)
    if parser is None:
        return sliding_window_chunks(content, file_path, language)

    tree = parser.parse(content.encode())
    chunks = []

    for node in walk_meaningful_nodes(tree.root_node, language):
        chunk_text = content[node.start_byte:node.end_byte]
        if len(chunk_text.strip()) < 20:   # skip trivial chunks
            continue
        chunks.append(RawChunk(
            content=chunk_text,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            language=language,
            node_type=node.type,
            name=extract_name(node, content),
        ))

    return chunks


def walk_meaningful_nodes(node, language: str):
    """
    Yield nodes that represent meaningful code units.
    For Python: function_definition, class_definition, decorated_definition
    For TypeScript: function_declaration, method_definition, class_declaration, arrow_function
    """
    TARGET_TYPES = {
        "python": {"function_definition", "class_definition", "decorated_definition"},
        "typescript": {"function_declaration", "method_definition", "class_declaration"},
    }
    targets = TARGET_TYPES.get(language, set())

    if node.type in targets:
        yield node
    else:
        for child in node.children:
            yield from walk_meaningful_nodes(child, language)
```

---

## Embedding Service

**Batch everything. Never embed one chunk at a time.**

```python
# app/services/embedding.py

import openai
import asyncio
from app.config import settings

client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Embed a list of texts in batches.
    Returns vectors in the same order as input.
    """
    if not texts:
        return []

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        # API returns embeddings in the same order as input
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """For embedding a PR diff at review time. Single call is fine here."""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=[text],
    )
    return response.data[0].embedding
```

---

## Retrieval Service

**The retrieval quality is the product quality. Get this right.**

```python
# app/services/retrieval.py

from sqlalchemy import text
from app.services.embedding import embed_single
from app.models.tables import CodeChunk

async def retrieve_chunks(
    repo_id: str,
    diff: str,
    top_k: int = 20,
) -> list[CodeChunk]:
    """
    Given a PR diff, retrieve the most relevant code chunks from the indexed repo.

    Strategy: embed the diff → cosine similarity search via pgvector → return top_k.

    The diff is embedded as-is. This works because the embedding model understands
    that a diff touching `calculate_discount` is semantically related to the function
    `calculate_discount` in the codebase.
    """
    diff_vector = await embed_single(diff)

    # pgvector cosine distance query
    # <=> is the cosine distance operator in pgvector
    # We want the lowest distance (most similar)
    result = db.execute(
        text("""
            SELECT *
            FROM code_chunks
            WHERE repo_id = :repo_id
            ORDER BY embedding <=> :query_vector
            LIMIT :top_k
        """),
        {
            "repo_id": repo_id,
            "query_vector": str(diff_vector),
            "top_k": top_k,
        }
    )

    return result.fetchall()
```

**What gets embedded as the query:**

Don't just embed the raw unified diff text. Enrich it:

```python
def build_retrieval_query(diff: str, pr_title: str) -> str:
    """
    Build a richer query for retrieval by combining the PR title
    (which often names the intent) with the diff (which shows the change).
    This improves recall for semantically relevant chunks.
    """
    return f"{pr_title}\n\n{diff}"
```

---

## Review Generation Service

**Prompt structure is load-bearing. Document it.**

```python
# app/services/review_gen.py

SYSTEM_PROMPT = """
You are a senior software engineer performing a code review.
You have access to relevant context from the codebase retrieved specifically for this PR.

Your review must:
1. Focus on correctness, security, performance, and maintainability — in that order
2. Be specific: reference exact code, not vague observations
3. When referencing a code chunk, cite it as [CHUNK_ID: N] — never invent line numbers
4. Return a valid JSON object matching the ReviewOut schema — nothing else

Severity definitions:
- high: will cause a bug, security issue, or data loss in production
- medium: likely to cause problems under load or edge cases
- low: style, readability, or minor improvement suggestions

Be direct. Be honest. If the PR is clean, say so briefly.
Do not pad the review with praise.
"""

async def generate_review(
    pr_id: str,
    diff: str,
    chunks: list[CodeChunk],
) -> ReviewOut:
    """
    Assemble the prompt, stream Claude's response, parse the ReviewOut JSON.
    Emits generation-chunk SSE events as text arrives.
    """
    # Format chunks with their IDs so the LLM can cite them
    context_block = format_chunks_for_prompt(chunks)

    user_message = f"""
## PR Diff

{diff}

## Relevant Codebase Context

{context_block}

## Instructions

Review this PR. Return only a valid JSON object matching the ReviewOut schema.
Cite code references using [CHUNK_ID: N] syntax.
"""

    full_response = ""
    async with anthropic_client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full_response += text
            emit_generation_chunk(pr_id=pr_id, text=text)

    return parse_review_json(full_response, pr_id=pr_id)


def format_chunks_for_prompt(chunks: list[CodeChunk]) -> str:
    """
    Format retrieved chunks so the LLM can reference them by ID.
    This is critical — without explicit IDs, the LLM invents line numbers.
    """
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(
            f"[CHUNK_ID: {i}] {chunk.file_path} lines {chunk.start_line}-{chunk.end_line}\n"
            f"```{chunk.language}\n{chunk.content}\n```"
        )
    return "\n\n".join(parts)


def parse_review_json(response: str, pr_id: str) -> ReviewOut:
    """
    Parse the LLM's JSON response into a ReviewOut object.
    Retries up to 2 times if the JSON is malformed.
    """
    try:
        data = json.loads(response.strip())
        return ReviewOut(**data, pr_id=pr_id)
    except (json.JSONDecodeError, ValidationError) as e:
        log.warning("review_json_parse_failed", error=str(e), pr_id=pr_id)
        raise ReviewParseError(f"Failed to parse review JSON: {e}")
```

---

## SSE Broadcasting

**SSE events are stored in Redis so late-connecting clients can replay them.**

```python
# app/services/pipeline_events.py

import json
import redis

def emit_stage(pr_id: str, stage: str, progress: float, message: str,
               duration_ms: float | None = None) -> None:
    event = {
        "type": "stage-update",
        "data": {
            "stage": stage,
            "progress": progress,
            "message": message,
            "duration_ms": duration_ms,
        }
    }
    _publish_and_store(pr_id, event)


def emit_generation_chunk(pr_id: str, text: str) -> None:
    event = {
        "type": "generation-chunk",
        "data": {"text": text}
    }
    # generation chunks are not stored — too many, too large
    redis_client.publish(f"review:{pr_id}", json.dumps(event))


def emit_complete(pr_id: str, review: ReviewOut) -> None:
    event = {
        "type": "complete",
        "data": review.model_dump()
    }
    _publish_and_store(pr_id, event)


def _publish_and_store(pr_id: str, event: dict) -> None:
    """
    Publish to Redis pub/sub (for live SSE connections)
    AND append to a Redis list (for late-connecting clients to replay).
    """
    serialized = json.dumps(event)
    redis_client.publish(f"review:{pr_id}", serialized)
    redis_client.rpush(f"review_events:{pr_id}", serialized)
    redis_client.expire(f"review_events:{pr_id}", 3600)  # 1 hour TTL


# In the SSE endpoint — handles both live and catch-up:
@router.get("/api/pr/{pr_id}/review/stream")
async def review_stream(pr_id: str, request: Request):
    async def event_generator():
        # First: replay any past events (handles late connect)
        past_events = redis_client.lrange(f"review_events:{pr_id}", 0, -1)
        for event in past_events:
            yield f"data: {event}\n\n"

        # Then: subscribe for future events
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"review:{pr_id}")
        async for message in pubsub.listen():
            if await request.is_disconnected():
                break
            if message["type"] == "message":
                yield f"data: {message['data']}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Auth — GitHub OAuth

**Session cookie only. No JWTs. No tokens in client-side storage.**

```python
# app/routers/auth.py

@router.get("/api/auth/github")
async def github_auth(response: Response):
    state = secrets.token_urlsafe(32)
    # Store state in Redis for CSRF validation
    redis_client.setex(f"oauth_state:{state}", 300, "1")
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&scope=repo"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/api/auth/callback")
async def github_callback(code: str, state: str, response: Response):
    # Validate CSRF state
    if not redis_client.get(f"oauth_state:{state}"):
        raise HTTPException(status_code=400, detail="Invalid state")
    redis_client.delete(f"oauth_state:{state}")

    # Exchange code for access token
    token = await exchange_github_code(code)

    # Encrypt before storing — never store plaintext tokens
    encrypted = fernet.encrypt(token.encode()).decode()

    # Upsert user
    user = upsert_user(github_token=token, encrypted_token=encrypted)

    # Set HttpOnly session cookie
    response.set_cookie(
        key="session",
        value=create_session_token(user.id),
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return RedirectResponse("/dashboard")
```

---

## Error Handling

**Errors are expected. Handle them at the right level.**

```python
# Custom exception hierarchy
class MeridianError(Exception):
    """Base exception. All app errors inherit from this."""
    pass

class GitHubAPIError(MeridianError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)

class IngestionError(MeridianError):
    pass

class RetrievalError(MeridianError):
    pass

class ReviewGenerationError(MeridianError):
    pass

class ReviewParseError(ReviewGenerationError):
    """LLM returned malformed JSON."""
    pass


# Global exception handler in main.py
@app.exception_handler(MeridianError)
async def meridian_error_handler(request: Request, exc: MeridianError):
    log.error("unhandled_meridian_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred", "detail": str(exc)}
    )
```

**In workers: catch, log, emit error event, re-raise.**

Workers should never swallow exceptions silently.
Re-raise after handling so RQ marks the job as failed and the job appears in the failed queue.

---

## Logging — structlog

**Every log line is JSON. Every log line has context.**

```python
# app/middleware/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger()

# In a service:
log = log.bind(repo_id=repo_id, pr_id=pr_id)
log.info("retrieval_complete", chunks_retrieved=len(chunks), duration_ms=elapsed)
log.error("llm_timeout", stage="generation", timeout_s=120)
```

**Minimum required fields on every log line:**
- `level`
- `timestamp`
- `event` (what happened)
- Contextual IDs: `repo_id`, `pr_id`, `job_id` — whatever applies

---

## Testing

**Services are pure functions where possible. Test them directly.**

```python
# tests/unit/test_chunking.py

def test_python_file_chunks_at_function_boundaries():
    source = """
def foo():
    return 1

def bar():
    return 2
"""
    chunks = parse_file(source, "test.py", "python")
    assert len(chunks) == 2
    assert chunks[0].name == "foo"
    assert chunks[1].name == "bar"


def test_short_chunks_are_skipped():
    source = "x = 1\n"
    chunks = parse_file(source, "test.py", "python")
    assert len(chunks) == 0


# tests/unit/test_retrieval.py — mock the DB and embedding service

async def test_retrieval_returns_top_k(mock_db, mock_embed):
    mock_embed.return_value = [0.1] * 1536
    mock_db.return_value = fake_chunks(count=20)

    result = await retrieve_chunks(repo_id="r1", diff="some diff", top_k=20)

    assert len(result) == 20
    mock_embed.assert_called_once()
```

**Integration tests use real Postgres + pgvector.**

```python
# tests/integration/test_ingestion.py
# Uses testcontainers-python to spin up a real Postgres instance

@pytest.fixture
def pg_container():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg

async def test_full_ingestion_pipeline(pg_container):
    # Run real ingestion against a fixture repo
    # Assert code_chunks table has expected rows
    # Assert embeddings are stored with correct dimensions
    pass
```

---

## What Not To Build (MVP Scope)

Real features. Build them later.

- Cross-encoder reranking — vector search alone is good enough to start
- BM25 hybrid search — add when you have users reporting retrieval misses
- Inline diff annotation resolver — citations as [CHUNK_ID: N] strings is fine for v1
- AcceptedPR history retrieval — create the table, leave the embedding column nullable
- Prometheus + Grafana — structlog JSON is enough for now
- Multi-region — single Railway instance is fine until you have the users
- Worker autoscaling — start with 2 fixed workers
