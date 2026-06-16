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


# --- SSE Events ---


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


# --- Ingestion ---


class IngestionStatusOut(BaseModel):
    job_id: str
    status: Literal["pending", "running", "complete", "failed"]
    files_ingested: Optional[int] = None
    current_step: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    error_message: Optional[str] = None

