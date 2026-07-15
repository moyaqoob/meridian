"""Pull request browse: list open PRs and fetch unified diffs from GitHub."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import PullFileOut, PullRequestDetailOut, PullRequestOut
from models.tables import User
from routers.auth import decrypt_access_token, get_current_user
from services import github as github_service

router = APIRouter(prefix="/api/prs", tags=["prs"])


def _full_name(owner: str, repo: str) -> str:
    return f"{owner}/{repo}"


def _pr_summary(item: dict) -> PullRequestOut:
    user = item.get("user") or {}
    base = item.get("base") or {}
    head = item.get("head") or {}
    return PullRequestOut(
        number=int(item["number"]),
        title=str(item.get("title") or ""),
        state=str(item.get("state") or "open"),
        author=str(user.get("login") or ""),
        html_url=str(item.get("html_url") or ""),
        updated_at=str(item.get("updated_at") or ""),
        base_branch=str(base.get("ref") or ""),
        head_branch=str(head.get("ref") or ""),
        additions=int(item.get("additions") or 0),
        deletions=int(item.get("deletions") or 0),
        changed_files=int(item.get("changed_files") or 0),
    )


@router.get("/{owner}/{repo}", response_model=list[PullRequestOut])
async def list_pull_requests(
    owner: str,
    repo: str,
    user: User = Depends(get_current_user),
) -> list[PullRequestOut]:
    """List open pull requests for a repository (newest updated first)."""
    token = decrypt_access_token(user.encrypted_access_token)
    remote = await github_service.list_pull_requests(token, _full_name(owner, repo))
    return [_pr_summary(item) for item in remote]


@router.get("/{owner}/{repo}/{number}", response_model=PullRequestDetailOut)
async def get_pull_request(
    owner: str,
    repo: str,
    number: int,
    user: User = Depends(get_current_user),
) -> PullRequestDetailOut:
    """Fetch PR metadata, changed files, and unified diff."""
    if number < 1:
        raise HTTPException(status_code=400, detail="PR number must be >= 1")

    token = decrypt_access_token(user.encrypted_access_token)
    full_name = _full_name(owner, repo)

    pr, diff, files = await asyncio.gather(
        github_service.get_pull_request(token, full_name, number),
        github_service.get_pull_diff(token, full_name, number),
        github_service.list_pull_files(token, full_name, number),
    )

    summary = _pr_summary(pr)
    return PullRequestDetailOut(
        **summary.model_dump(),
        body=pr.get("body"),
        diff=diff,
        files=[
            PullFileOut(
                filename=str(f.get("filename") or ""),
                status=str(f.get("status") or "modified"),
                additions=int(f.get("additions") or 0),
                deletions=int(f.get("deletions") or 0),
            )
            for f in files
            if f.get("filename")
        ],
    )
