from typing import Literal, List, Dict, Optional

from pydantic import BaseModel



class ReviewFinding(BaseModel):
    id: str
    severity: Literal["high", "medium", "low"]
    category: str
    title: str
    comment: str
    file_path: Optional[str] = None
    chunk_ref: Optional[str] = None  # "[CHUNK_ID: N]" reference from LLM


class ReviewOut(BaseModel):
    review_id: str
    pr_id: str
    summary: str
    pr_type: Literal["feat", "fix", "refactor", "chore"]
    findings: List[ReviewFinding]
    model_version: str
    timings: Dict[str, float]  # stage -> duration_ms



class StageUpdateEvent(BaseModel):
    stage: Literal["validation", "retrieval", "generation", "citation-mapping", "complete"]
    progress: float  # 0.0 to 1.0
    message: str
    duration_ms: Optional[float] = None


class GenerationChunkEvent(BaseModel):
    text: str
    phase: Literal["summary", "findings"]


class CompleteEvent(BaseModel):
    review_id: str
    status: Literal["complete"]
    summary: str
    findings: List[ReviewFinding]
    timings: Dict[str, float]


class ErrorEvent(BaseModel):
    stage: str
    message: str
    retryable: bool


# --- Auth ---


class UserOut(BaseModel):
    id: str
    github_id: int
    login: str


class SessionOut(BaseModel):
    authenticated: bool
    user: Optional[UserOut] = None


# --- Repos ---


class RepoOut(BaseModel):
    id: str
    github_repo_id: int
    full_name: str
    default_branch: str
    ingest_status: Literal["pending", "processing", "ready", "failed"]
    files_ingested: Optional[int] = None
    ingest_error: Optional[str] = None


class ConnectRepoRequest(BaseModel):
    full_name: str  # "owner/repo"


class GitHubRepoOut(BaseModel):
    github_repo_id: int
    full_name: str
    default_branch: str
    private: bool
    connected: bool


class EmbedRepoRequest(BaseModel):
    repo_id: str
    repo_path: str


# --- Ingestion (v1: sourced from Repo, not IngestionJob) ---


class IngestionStatusOut(BaseModel):
    repo_id: str
    status: Literal["pending", "processing", "ready", "failed"]
    files_ingested: Optional[int] = None
    error_message: Optional[str] = None

