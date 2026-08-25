#!/usr/bin/env bash
# One-command Meridian local stack: Docker + API + RQ worker + Next.js
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/apps/backend"
WEB="$ROOT/apps/web"

echo "==> Syncing Postgres env from DATABASE_URL"
(cd "$BACKEND" && uv run python scripts/sync_postgres_env.py)

echo "==> Starting Postgres + Redis"
(cd "$BACKEND" && docker compose up -d)

echo "==> Waiting for Postgres + Redis"
for i in $(seq 1 40); do
  if docker exec meridian-db pg_isready -U "${POSTGRES_USER:-user}" >/dev/null 2>&1 \
    && docker exec meridian-redis redis-cli ping >/dev/null 2>&1; then
    break
  fi
  sleep 1
  if [ "$i" -eq 40 ]; then
    echo "Docker services did not become healthy. Is Docker Desktop running?"
    exit 1
  fi
done

cleanup() {
  echo "==> Stopping API / worker / web (Docker left running)"
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> API on :8000"
(cd "$BACKEND" && uv run main.py) &

echo "==> RQ worker (ingest + reviews)"
(cd "$BACKEND" && uv run rq worker meridian-ingest meridian-reviews) &

echo "==> Web on :3000"
(cd "$WEB" && bun dev) &

echo ""
echo "Meridian is starting."
echo "  Web:    http://localhost:3000"
echo "  API:    http://localhost:8000/api/health"
echo "  Worker: meridian-ingest + meridian-reviews"
echo ""
echo "Press Ctrl+C to stop API/worker/web (Docker keeps running)."
wait
