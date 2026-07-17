# Backend

## Local infrastructure

Postgres + pgvector and Redis run via Docker Compose.

```bash
cd apps/backend
uv run python scripts/sync_postgres_env.py   # sync POSTGRES_* from DATABASE_URL
docker compose up -d
uv run main.py
```

Meridian Postgres listens on **5434** by default so it does not clash with a local Windows Postgres on 5432. `DATABASE_URL` must use that port (example):

```env
DATABASE_URL=postgresql://user:pass@localhost:5434/meridian
REDIS_URL=redis://localhost:6379/0
```

## Tests

```bash
uv run pytest -q
```
