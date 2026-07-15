---
description: project rules
alwaysApply: false
---


# Meridian — Cursor Project Rules

## What This Project Is

Meridian is an AI-powered code reviewer. It indexes a GitHub repository, and when a pull request is opened, it retrieves relevant code context from that index and generates a structured review using an LLM.

It is a **retrieval system with an LLM at the end** — not an LLM wrapper.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (TypeScript / React) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + pgvector |
| Queue | Redis + RQ |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic Claude Sonnet |
| Code parsing | tree-sitter |
| Auth | GitHub OAuth |
| Deployment | Vercel (frontend) + Railway (backend) |


---

## The Two Core Pipelines

### 1. Indexing (runs once on repo connect)
```
user connects repo
→ clone/fetch codebase via GitHub API
→ tree-sitter splits files into chunks (function / class / method boundaries)
→ embed each chunk → text-embedding-3-small → vector(1536)
→ store in code_chunks table with pgvector
→ mark repo ingest_status = "ready"
```

### 2. Review (runs on every PR)
```
PR opened on GitHub
→ webhook fires → POST /api/webhooks/github
→ webhook handler: verify HMAC, dedupe via Redis, enqueue job, return 200 immediately
→ background worker picks up job
→ fetch PR diff from GitHub API
→ embed diff → search code_chunks by cosine similarity → top 20 chunks
→ prompt: system + diff + top 20 chunks + JSON schema
→ stream Claude response
→ store Review + annotations
→ SSE pushes pipeline stages to frontend live
```

**The webhook handler never does real work. It always hands off to the worker immediately.**

---

## Data Model

### `users`
- `id`, `github_id`, `login`, `encrypted_access_token`, `created_at`

### `repos`
- `id`, `user_id`, `github_repo_id`, `full_name`, `default_branch`
- `ingest_status` — enum: `pending | processing | ready | failed`

### `code_chunks`
- `id`, `repo_id`, `file_path`, `start_line`, `end_line`
- `language`, `content`, `checksum`
- `embedding vector(1536)` — pgvector column

### `prs`
- `id`, `repo_id`, `github_pr_id`, `number`, `title`
- `head_sha`, `base_sha`, `status`

### `reviews`
- `id`, `pr_id`, `summary`, `structured_json`, `model_version`, `created_at`

### `review_annotations`
- `id`, `review_id`, `file_path`, `line_start`, `line_end`
- `comment`, `severity` — enum: `high | medium | low`
- `category` — e.g. `performance`, `security`, `test_coverage`

### `ingestion_jobs`
- `id`, `repo_id`, `status`, `started_at`, `finished_at`
- `files_ingested`, `error_message`

### `accepted_prs` *(planned — v2)*
- `id`, `repo_id`, `pr_number`, `title`, `diff`, `review_summary`
- `merged_at`, `embedding vector(1536)`
- Purpose: store merged PRs so future reviews can retrieve historical decisions as context

---

## REST API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/auth/github` | Start GitHub OAuth |
| `GET` | `/api/auth/callback` | OAuth callback, set session cookie |
| `GET` | `/api/repos` | List connected repos |
| `POST` | `/api/repos/connect` | Connect a repo, trigger ingestion |
| `GET` | `/api/ingest/{job_id}` | Poll ingestion status |
| `GET` | `/api/pr/{id}/review/stream` | SSE stream for live review pipeline |
| `POST` | `/api/review/trigger` | Manually trigger a review |
| `POST` | `/api/webhooks/github` | GitHub webhook receiver |

---

## SSE Event Shapes

The frontend opens an SSE connection to `/api/pr/{id}/review/stream`.
The worker emits these events as pipeline stages complete:

```
event: stage-update
data: {"stage": "retrieval", "progress": 0.4, "message": "Retrieved 18 chunks", "duration_ms": 1240}

event: generation-chunk
data: {"text": "## Architectural Concerns\n...", "phase": "summary"}

event: complete
data: {"review_id": "uuid", "summary": "...", "annotations": [...], "timings": {...}}

event: error
data: {"stage": "retrieval", "message": "pgvector timeout", "retryable": true}
```

**Important:** if the client connects after the job has already started or finished, the backend must return current state + replay past events for that review. Do not assume the client connects at job start.

---

## Backend File Structure

```
backend/
  app/
    main.py
    config.py           # Pydantic Settings — all env vars live here
    deps.py             # DB session, auth, rate limiting as FastAPI dependencies
    routers/
      auth.py
      repos.py
      review.py
      webhooks.py
    services/
      github.py         # GitHub App client — API calls, diff fetching
      ingestion.py      # clone → parse → chunk → embed → store
      retrieval.py      # embed diff → pgvector search → return top-k chunks
      review_gen.py     # assemble prompt → stream Claude → parse ReviewOut
      pipeline_events.py  # SSE event construction
    workers/
      ingest_worker.py
      review_worker.py
    models/
      sqlalchemy/       # ORM table definitions
      schemas/          # Pydantic request/response schemas
  tests/
  Dockerfile
  pyproject.toml
  
```

---

## Frontend File Structure

```
src/
  app/
    page.tsx                          # Landing
    dashboard/                        # Repo list + ingestion status
    repo/[owner]/[repo]/              # Repo settings
    pr/[owner]/[repo]/[number]/       # 3-panel review page
  components/
    pr/diff-panel.tsx                 # Left: PR diff
    pr/pipeline-panel.tsx             # Middle: live pipeline stages
    pr/review-panel.tsx               # Right: structured findings
  lib/api/client.ts
  lib/api/endpoints.ts
```

---

## Core Rules

**Retrieval:**
- Chunks are split at function/class/method boundaries using tree-sitter, not by character count
- Each chunk stores: file_path, start_line, end_line, content, checksum, embedding
- Retrieval embeds the PR diff and runs cosine similarity search against code_chunks
- Skip cross-encoder reranking in MVP — plain vector search is sufficient to start
- Skip BM25 hybrid search in MVP — add it when retrieval quality becomes a felt problem

**Background jobs:**
- Webhook endpoint must return 200 in under 2 seconds — never do real work inline
- Deduplicate webhooks using `X-GitHub-Delivery` UUID stored in Redis with 24h TTL
- Workers handle: fetch diff → retrieve → generate → store → emit SSE events

**Idempotency:**
- Every review trigger must be idempotent — same PR + same SHA should not produce a second review
- Use `(repo_id, pr_number, head_sha)` as the natural dedup key

**Embeddings:**
- Model: `text-embedding-3-small`, 1536 dimensions
- Cache embeddings per `(repo_id, file_path, sha)` — skip re-embedding unchanged files
- Batch embedding calls, never embed one chunk at a time in a loop

**LLM:**
- Model: Claude Sonnet (latest)
- Always stream the response — never wait for full completion before sending to client
- Prompt structure: system message → retrieved chunks with [CHUNK_ID] labels → PR diff → JSON schema
- Ask LLM to cite references as [CHUNK_ID: N], not as line numbers — line numbers drift

**Security:**
- Verify GitHub webhook HMAC-SHA256 signature on every incoming webhook
- Store GitHub access tokens encrypted at rest (Fernet)
- Session via HttpOnly, Secure, SameSite=Strict cookie — never expose token to client JS

**What not to build in MVP:**
- Cross-encoder reranking
- BM25 hybrid search
- Inline diff annotations (show review as text first)
- accepted_prs history retrieval (add the table, leave it empty)
- Grafana / Prometheus / OpenTelemetry (structured logs are enough)
- Staging environment (local + production is fine)

---

## What Good Looks Like

A working Meridian MVP does exactly this:

1. User signs in with GitHub
2. User connects a repo → ingestion runs → status shows "Ready"
3. User opens a PR on GitHub → webhook fires → review job runs
4. User opens the PR page in Meridian → sees pipeline stages → sees structured review

Everything else is polish. Ship this loop first.
