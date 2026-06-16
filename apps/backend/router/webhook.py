import os
import httpx
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/webhook", tags=["webhook"])

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

@router.post("/github")
async def github_webhook(request: Request) -> dict:
    payload = await request.json()

    if "pull_request" not in payload:
        return {"status": "ignored", "reason": "not a pull request event"}

    pr = payload["pull_request"]
    repo = payload["repository"]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    pr_number = pr["number"]

    url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Pull request not found")
    if not response.is_success:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error: {response.text}",
        )

    return {
        "action": payload.get("action"),
        "pull_request": response.json(),
    }
