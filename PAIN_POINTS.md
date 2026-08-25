# Meridian — where it breaks (ops checklist)

If login → ingest → open → PR review fails, check these in order. Most “forever Indexing” bugs are #1–#3.

| # | Failure | Symptom | Fix |
|---|---|---|---|
| 1 | **Docker Desktop not running** | API crash on boot, health `database.ok=false` / `redis.ok=false`, OAuth fails | Start Docker Desktop → `bun run dev:infra` or `scripts/dev.ps1` |
| 2 | **RQ worker not running** | Ingest stuck on Indexing; Approve/webhook never finishes | `bun run dev:worker` (queues: `meridian-ingest` + `meridian-reviews`) |
| 3 | **Only `bun run dev` / turbo** | API+web up, no Postgres/Redis/worker | Use `bun run dev:stack` / `scripts/dev.ps1` |
| 4 | **Bad / expired GitHub token** | `git clone` auth failed | Sign out + sign in (needs `repo` scope) |
| 5 | **NVIDIA_API_KEY invalid** | Ingest Failed during embed | Fix key in `apps/backend/.env`, Retry ingest |
| 6 | **Webhook not pointed at API** | PRs never auto-review (manual Approve still works) | GitHub webhook → `POST /webhook/github` + `GITHUB_WEBHOOK_SECRET` |
| 7 | **Repo not Ready** | Open disabled / workspace redirects to dashboard | Wait for Ready or Retry ingest |
| 8 | **Empty indexable tree** | Ready with 0 files; weak reviews | Repo has no `.py/.ts/.tsx/.js/.jsx/.rs` outside skip dirs |
| 9 | **Port clash** | DB won’t start | `DATABASE_URL` / `POSTGRES_PORT` use **5434** by default |
| 10 | **Fernet / session secret rotated** | Decrypt errors / forced re-login | Keep `FERNET_KEY` + `SESSION_SECRET` stable |

## Healthy local shape

```
Docker:  meridian-db + meridian-redis
API:     :8000   GET /api/health → status ok
Worker:  rq worker meridian-ingest meridian-reviews
Web:     :3000
```

## Ingest path (after this fix)

`POST /api/repos/{id}/ingest` → Redis RQ (`meridian-ingest`) → worker clones → chunks → embeds → `ready`/`failed`.

Survives API restart/reload. Without the worker, the job sits in Redis and the UI stays Indexing — click **Re-queue ingest** after starting the worker.
