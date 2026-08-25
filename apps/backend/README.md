# Backend

## One-command local stack (recommended)

**Windows (PowerShell):**

```powershell
# Docker Desktop must be running first
pwsh -File scripts/dev.ps1
# or: bun run dev:stack
```

This opens three terminals: API `:8000`, RQ worker (ingest + reviews), web `:3000`.

**Manual (any OS):**

```bash
cd apps/backend
uv run python scripts/sync_postgres_env.py
docker compose up -d
uv run main.py                                          # terminal 1
uv run rq worker meridian-ingest meridian-reviews       # terminal 2
cd ../web && bun dev                                    # terminal 3
```

Without the **RQ worker**, Ingest stays on “Indexing” forever and PR reviews never run.

Check health: [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Env

Meridian Postgres listens on **5434** by default so it does not clash with a local Windows Postgres on 5432:

```env
DATABASE_URL=postgresql://user:pass@localhost:5434/meridian
REDIS_URL=redis://localhost:6379/0
```

`bun run dev` / `turbo dev` only starts API + web — **not** Docker or the worker. Prefer `dev:stack`.

## Product loop

1. Sign in with GitHub (`repo` scope)
2. Dashboard → **Ingest** a repo → wait until **Ready**
3. **Open** the workspace
4. Open a PR on GitHub (webhook → auto review) **or** click **Approve review**
5. Pipeline stages stream live via SSE; findings persist in Postgres

Webhook URL: `POST http://<your-host>:8000/webhook/github`  
Secret: same as `GITHUB_WEBHOOK_SECRET`

## Phase 2 acceptance

1. **Webhook → auto review** — Open a PR on a connected, ingested repo. Pipeline advances without Approve (~30s if worker is up).
2. **SSE replay** — Reload mid-review; stages replay from Redis Streams.
3. **Dedup** — Redeliver same `X-GitHub-Delivery` → `{"status":"duplicate"}`.
4. **Idempotent review** — Same `(repo, pr, head_sha)` never creates two review rows.

```bash
uv run python scripts/smoke_webhook.py --github-repo-id <id> --pr 1 --sha <head_sha>
```

## Tests

```bash
uv run pytest -q
```
