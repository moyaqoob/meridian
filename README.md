# Meridian

> **AI code review that has actually read your codebase.**

A developer opens a pull request. Meridian fetches the diff, searches your entire indexed codebase for relevant context, and streams a structured, line-annotated review — live — in under 20 seconds.

This is not a wrapper around an LLM. It's a **retrieval system with an LLM at the end.** That distinction is what makes it work.

---

## What It Does

```
Developer opens PR on GitHub
        │
        ▼
GitHub sends webhook → Meridian receives it
        │
        ▼
Worker fetches the diff + changed symbols
        │
        ▼
Hybrid search across indexed codebase
  ├─ BM25 full-text  (finds exact function names)
  └─ Vector search   (finds semantically similar code)
        │
        ▼
Cross-encoder reranker → top 20 chunks
        │
        ▼
Claude Sonnet reads: diff + context + schema
        │
        ▼
Structured review streams to the UI — live
  ├─ Findings with severity
  ├─ Line-level annotations on the diff
  └─ Cited evidence from your codebase
```

---

## The Pipeline, Step by Step

### 1 — Indexing your repository

Before any review can happen, Meridian needs to understand your codebase. This happens once (and incrementally on changes):

```
Clone repo
    │
    ▼
Walk file tree → filter by language
    │
    ▼
tree-sitter parse → functions, classes, methods
    │
    ▼
Batch embed with text-embedding-3-small
    │
    ▼
Store chunks + vectors in PostgreSQL (pgvector)
    │
    ▼
Repo status: READY
```

Every chunk is stored with its file path, line range, and a content checksum. On subsequent indexing runs, **unchanged files are skipped entirely** — targeting 70–90% cache hit after the first ingestion.

**Cost:** a 10k LOC repo costs ~$0.008 to embed. A 100k LOC repo costs ~$0.08.

---

### 2 — Retrieval: finding what's relevant

When a PR opens, the retrieval stage answers: *which parts of the codebase does this diff touch, call, or affect?*

```
PR diff + changed symbol names
         │
         ▼
    ┌────┴────┐
    ▼         ▼
  BM25      Vector
  search    search
  (exact    (semantic
  names)    similarity)
    │         │
    └────┬────┘
         ▼
   RRF merge → top 50
         │
         ▼
  Cross-encoder rerank
         │
         ▼
     top 20 chunks
     → passed to LLM
```

**Why two search systems?** BM25 is exact — it finds `process_payment` if the diff calls `process_payment`. Vector search is fuzzy — it finds code that *behaves like* the changed code, even with different names. RRF (Reciprocal Rank Fusion) merges both lists without needing to tune weights. The cross-encoder reranker makes a final pass, scoring each chunk against the full diff context.

---

### 3 — Generation: the LLM as a reasoning layer

The LLM doesn't *know* your codebase. It *reads* the 20 relevant chunks you hand it, along with the diff, and reasons about them. This is the correct mental model.

```
System prompt
    + top 20 retrieved chunks
    + PR diff
    + ReviewOut JSON schema
         │
         ▼
  Claude Sonnet 4 (streaming)
         │
         ▼
  Structured JSON: {
    summary,
    findings: [{ severity, file, line, message, evidence }],
    classification: feat|fix|refactor|chore
  }
         │
         ▼
  Parse + validate (retry ×2 if malformed)
```

The LLM output is **schema-constrained**. Every finding includes a file path, line reference, severity, and a cited evidence chunk. There is no free-form "general thoughts" field — the structure is enforced.

---

### 4 — Citation mapping: anchoring to the diff

Raw LLM output references `file:line` positions. These need to be resolved against the actual diff hunk positions so annotations can be pinned to exact diff lines in the UI.

```
ReviewOut findings
      │
      ▼
Extract file:line references
      │
      ▼
Match against diff hunk positions
      │
      ▼
Create ReviewAnnotation rows
      │
      ▼
Annotations available in UI
```

---

## System Architecture

```
┌─────────────────────────────────────────────┐
│              Next.js Client                  │
│   Auth · Dashboard · 3-Panel PR Review UI    │
│   Pipeline visualizer · Diff annotations     │
└──────────────────┬──────────────────────────┘
                   │  REST + SSE
                   ▼
┌─────────────────────────────────────────────┐
│              FastAPI Backend                 │
│                                             │
│  GitHub App / Webhook receiver              │
│  Ingestion orchestrator                     │
│  Retrieval service  (BM25 + vector + RRF)   │
│  LLM gateway        (streaming)             │
│  Citation resolver                          │
│  SSE broadcaster                            │
│                                             │
│       ┌────────────┐  ┌─────────────┐       │
│       │   Worker   │  │  Scheduler  │       │
│       │  (RQ/Arq)  │  │ (Celery Beat│       │
│       └────────────┘  └─────────────┘       │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┼───────────────┐
    ▼            ▼               ▼
┌──────────┐ ┌────────┐ ┌───────────────┐
│PostgreSQL│ │ Redis  │ │Object Storage │
│+pgvector │ │cache / │ │repo archives  │
│chunks,   │ │queues /│ │embedding      │
│reviews   │ │rate lim│ │artifacts      │
└──────────┘ └────────┘ └───────────────┘
```

**The API layer is stateless.** All work happens in workers. Scaling under load means adding worker processes, not API replicas.

---

## The Live Review UI

The PR review page is a **three-panel layout**:

```
┌─────────────────┬──────────────┬─────────────────┐
│                 │              │                 │
│   Diff panel    │  Pipeline    │  Review panel   │
│                 │  panel       │                 │
│  src/reviewer.py│              │  ## Findings    │
│                 │ ✓ Retrieval  │                 │
│  - if not ctx:  │   (20 chunks)│  ⚠ Error        │
│  + if len == 0: │ ⟳ Generating │  handling       │
│    raise ...    │ ◌ Citations  │  missing on     │
│  ← annotation   │ ◌ Complete   │  line 51 →      │
│                 │              │                 │
└─────────────────┴──────────────┴─────────────────┘
```

The pipeline panel streams events in real time. The user watches the review being assembled — not a spinner, not a wall of text that appears all at once. Every stage is visible, timed, and auditable.

---

## Event Stream

Communication from backend to client uses **Server-Sent Events (SSE)**. The event model is explicit:

| Event | When | Payload |
|---|---|---|
| `stage-update` | Each pipeline stage completes | stage, progress, message, duration_ms |
| `generation-chunk` | LLM streams a token batch | text, phase |
| `complete` | Review is done | review_id, summary, annotations, timings |
| `error` | Any stage fails | stage, message, retryable |

```
event: stage-update
data: {"stage": "retrieval", "progress": 1.0, "message": "Retrieved 20 chunks", "duration_ms": 380}

event: generation-chunk
data: {"text": "## Architectural Concerns\n...", "phase": "summary"}

event: complete
data: {"review_id": "...", "status": "complete", "annotations": [...]}
```

---

## Data Model (Core Tables)

```
repos
  id, owner, name, installation_id
  ingest_status: pending|indexing|ready|failed
  last_ingested_at

code_chunks
  id, repo_id, file_path, start_line, end_line
  content, content_checksum
  embedding vector(1536)        ← pgvector column
  language, chunk_type

pull_requests
  id, repo_id, pr_number, title
  head_sha, base_sha, diff_text
  status: pending|running|reviewed|failed

reviews
  id, pr_id, summary, classification
  timings (JSON), created_at

review_annotations
  id, review_id, file_path, diff_line
  severity: critical|warning|info
  message, evidence_chunk_id
```

---

## Production Concerns

### Resilience

| Scenario | What happens |
|---|---|
| Webhook delivered twice | Redis deduplication via `X-GitHub-Delivery` UUID (24h TTL) |
| LLM timeout or 5xx | Retry with smaller context; fallback to heuristic rules |
| Reranker unavailable | Skip reranking; pass raw RRF results to LLM |
| Vector search returns < 5 chunks | Supplement with BM25 results |
| Large repo (500k+ LOC) | Budget chunks: embed only changed files + direct imports; skip vendor/test dirs |

### Performance Targets

```
Ingestion:   10k LOC repo    → < 60s end-to-end
Retrieval:   hybrid search   → p95 < 400ms
             reranking       → p95 < 200ms
Generation:  first SSE chunk → < 800ms
             full review     → 8–20s
Client:      PR page TTI     → < 2s on 3G
Concurrency: 200 simultaneous review jobs
```

### Security

- Webhook HMAC-SHA256 verification on every GitHub event
- GitHub `access_token` encrypted at rest (Fernet)
- HttpOnly, Secure, SameSite=Strict session cookies
- Per-user Redis sliding-window rate limiting
- No PII stored beyond GitHub login + user ID

### Observability

| Layer | Tool | What's measured |
|---|---|---|
| Structured logging | `structlog` → JSON | request_id, stage, duration, error class |
| Tracing | OpenTelemetry | end-to-end: webhook → ingest → retrieve → generate → stream |
| Metrics | Prometheus | queue depth, LLM latency, retrieval recall@k, error rate |
| Errors | Sentry | unhandled exceptions + job failures with GitHub context |
| Dashboards | Grafana | ingestion throughput, review latency p50/p95, token spend |

---

## Cost Model

| Component | Unit Cost | Per Review |
|---|---|---|
| Embeddings | $0.02 / 1M tokens | ~$0.001 (retrieval query) |
| Claude Sonnet 4 | $3 input / $15 output / 1M tokens | ~$0.24 |
| Reranker (Cohere) | ~$0.001/query | ~$0.001 |
| **Total** | | **~$0.24 per review** |

First ingestion of a 10k LOC repo: ~$0.008. Subsequent runs: near-zero for unchanged files.

---

## Stack

| Layer | Technology |
|---|---|
| Client | Next.js + React (TypeScript) |
| Backend | FastAPI (Python) |
| Workers | RQ / Arq + Celery Beat |
| Database | PostgreSQL + pgvector |
| Cache / Queues | Redis |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic Claude Sonnet 4 |
| Reranker | Cohere cross-encoder (or local HuggingFace) |
| Parsing | tree-sitter |
| Code parsing | AST-based chunking per language |
| Infra | Vercel (client) + Railway (backend) + Supabase (DB) |
| Observability | OpenTelemetry + Prometheus + Grafana + Sentry |

---

## Local Development

```bash
# Clone and configure
git clone https://github.com/yaqoob/meridian
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, OPENAI_API_KEY, GITHUB_APP_ID, GITHUB_PRIVATE_KEY

# Start everything
docker compose up

# Apply migrations
python scripts/migrate.py

# Backend available at:  http://localhost:8000
# Client available at:   http://localhost:3000
```

---

## CI/CD

```
Pull Request opened
    │
    ├─ lint + typecheck (ruff / mypy / tsc)
    ├─ unit tests       (pytest / Vitest)
    ├─ integration tests (pytest + testcontainers)
    └─ preview deploy   (pr-*.vercel.app + ephemeral DB)

Merge to main
    └─ staging deploy   (staging.meridian.dev)

Git tag v*
    └─ production deploy (meridian.dev)
```

---

*Mohammed Yaqoob — Backend-focused Software Engineer*
*Stack: TypeScript client · Python backend · RAG-native architecture*
