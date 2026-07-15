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


async def list_pull_requests(
    access_token: str,
    full_name: str,
    *,
    state: str = "open",
    per_page: int = 30,
) -> list[dict]:
    """List pull requests for a repo, newest first."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://api.github.com/repos/{full_name}/pulls",
            headers=_headers(access_token),
            params={"state": state, "sort": "updated", "direction": "desc", "per_page": per_page},
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"GitHub repo not found: {full_name}")
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub list pulls failed: {response.text}",
        )
    return response.json()


async def get_pull_request(access_token: str, full_name: str, number: int) -> dict:
    """Fetch a single pull request by number."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://api.github.com/repos/{full_name}/pulls/{number}",
            headers=_headers(access_token),
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Pull request not found: {full_name}#{number}")
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub get pull failed: {response.text}",
        )
    return response.json()


async def get_pull_diff(access_token: str, full_name: str, number: int) -> str:
    """Fetch the unified diff for a pull request."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"https://api.github.com/repos/{full_name}/pulls/{number}",
            headers={
                **_headers(access_token),
                "Accept": "application/vnd.github.diff",
            },
        )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Pull request not found: {full_name}#{number}")
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub get pull diff failed: {response.text}",
        )
    return response.text


async def list_pull_files(
    access_token: str,
    full_name: str,
    number: int,
    *,
    per_page: int = 100,
) -> list[dict]:
    """List files changed in a pull request."""
    files: list[dict] = []
    page = 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(
                f"https://api.github.com/repos/{full_name}/pulls/{number}/files",
                headers=_headers(access_token),
                params={"per_page": per_page, "page": page},
            )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pull request not found: {full_name}#{number}",
                )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="GitHub token invalid or expired")
            if not response.is_success:
                raise HTTPException(
                    status_code=502,
                    detail=f"GitHub list pull files failed: {response.text}",
                )

            batch = response.json()
            if not batch:
                break
            files.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

    return files
