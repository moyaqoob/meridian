#!/usr/bin/env python3
"""Sync docker-compose Postgres env vars from DATABASE_URL in .env."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _load_database_url() -> str:
    if not ENV_PATH.exists():
        raise SystemExit(f"Missing {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("DATABASE_URL="):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DATABASE_URL not found in .env")


def _upsert_env(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        matched = False
        for key, value in updates.items():
            if re.match(rf"^{re.escape(key)}=", line):
                out.append(f"{key}={value}")
                seen.add(key)
                matched = True
                break
        if not matched:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    parsed = urlparse(_load_database_url())
    if not parsed.username or not parsed.password or not parsed.path.strip("/"):
        raise SystemExit("DATABASE_URL must include user, password, and database name")

    updates = {
        "POSTGRES_USER": unquote(parsed.username),
        "POSTGRES_PASSWORD": unquote(parsed.password),
        "POSTGRES_DB": unquote(parsed.path.lstrip("/")),
        "POSTGRES_PORT": str(parsed.port or 5432),
    }
    _upsert_env(updates)
    print("Synced POSTGRES_* from DATABASE_URL into .env")


if __name__ == "__main__":
    main()
