"""GitHub API helpers using the user's OAuth access token."""

from __future__ import annotations

import httpx
from fastapi import HTTPException


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def list_user_repos(access_token: str, *, per_page: int = 100) -> list[dict]:
    """Repos GitHub repos the authenticated user can access."""
    repos: list[dict] = []
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers=_headers(access_token),
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
            if not response.is_success:
                raise HTTPException(
                    status_code=502,
                    detail=f"GitHub list repos failed: {response.text}",
                )

            batch = response.json()
            if not batch:
                break
            repos.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

    return repos


async def get_repo(access_token: str, full_name: str) -> dict:
    """Fetch a single repo by owner/name."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://api.github.com/repos/{full_name}",
            headers=_headers(access_token),
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"GitHub repo not found: {full_name}")
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub get repo failed: {response.text}",
        )
    return response.json()
