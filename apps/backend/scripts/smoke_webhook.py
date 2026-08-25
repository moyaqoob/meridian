#!/usr/bin/env python3
"""
Fire a signed pull_request.opened webhook at a running Meridian API.

Usage:
  uv run python scripts/smoke_webhook.py --github-repo-id 12345 --pr 7 --sha abcdef
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import uuid

import httpx

from core.config import settings


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test GitHub webhook handler")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--github-repo-id", type=int, required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--delivery", default=None)
    args = parser.parse_args()

    delivery = args.delivery or str(uuid.uuid4())
    payload = {
        "action": "opened",
        "pull_request": {
            "number": args.pr,
            "head": {"sha": args.sha},
        },
        "repository": {"id": args.github_repo_id},
    }
    body = json.dumps(payload).encode()
    secret = settings.github_webhook_secret.get_secret_value()
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": delivery,
        "X-Hub-Signature-256": _sign(body, secret),
    }

    url = f"{args.base_url.rstrip('/')}/webhook/github"
    response = httpx.post(url, content=body, headers=headers, timeout=10.0)
    print(f"POST {url} -> {response.status_code}")
    print(response.text)

    # Redeliver same payload — expect duplicate
    response2 = httpx.post(url, content=body, headers=headers, timeout=10.0)
    print(f"Redeliver -> {response2.status_code} {response2.text}")

    if response.status_code != 200:
        return 1
    if response2.json().get("status") != "duplicate":
        print("Expected duplicate on redelivery", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
