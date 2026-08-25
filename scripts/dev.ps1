# One-command Meridian local stack for Windows (PowerShell)
# Usage:  pwsh -File scripts/dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "apps\backend"
$Web = Join-Path $Root "apps\web"

Write-Host "==> Syncing Postgres env from DATABASE_URL"
Push-Location $Backend
uv run python scripts/sync_postgres_env.py
Pop-Location

Write-Host "==> Starting Postgres + Redis (requires Docker Desktop)"
Push-Location $Backend
docker compose up -d
if ($LASTEXITCODE -ne 0) {
  Write-Error "docker compose failed. Start Docker Desktop, then re-run this script."
}
Pop-Location

Write-Host "==> Waiting for healthy containers"
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
  docker exec meridian-db pg_isready 2>$null | Out-Null
  $dbOk = ($LASTEXITCODE -eq 0)
  docker exec meridian-redis redis-cli ping 2>$null | Out-Null
  $redisOk = ($LASTEXITCODE -eq 0)
  if ($dbOk -and $redisOk) { $ok = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ok) {
  Write-Error "Postgres/Redis never became healthy. Is Docker Desktop running?"
}

Write-Host "==> Starting API, RQ worker, and web (3 windows)"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$Backend'; Write-Host 'API :8000'; uv run main.py"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$Backend'; Write-Host 'RQ worker'; uv run rq worker meridian-ingest meridian-reviews"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$Web'; Write-Host 'Web :3000'; bun dev"

Write-Host ""
Write-Host "Opened 3 terminals:"
Write-Host "  Web:    http://localhost:3000"
Write-Host "  API:    http://localhost:8000/api/health"
Write-Host "  Worker: meridian-ingest + meridian-reviews"
Write-Host ""
Write-Host "Login → Ingest a repo → Open → open a PR on GitHub (webhook) or Approve in UI."
