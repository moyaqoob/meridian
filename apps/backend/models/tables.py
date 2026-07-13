from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id = Column(Integer, unique=True, nullable=False)
    login = Column(String, nullable=False)
    encrypted_access_token = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    repos = relationship("Repo", back_populates="user")

class Repo(Base):
    __tablename__ = "repos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # v1: single owner
    github_repo_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    default_branch = Column(String, nullable=False)
    ingest_status = Column(
        Enum("pending", "processing", "ready", "failed", name="ingest_status_enum"),
        nullable=False,
        default="pending"
    )
    files_ingested = Column(Integer, nullable=True)
    ingest_error = Column(Text, nullable=True)

class CodeChunk(Base):
    __tablename__ = "code_chunks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    file_path = Column(String, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    language = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    checksum = Column(String, nullable=False)
    embedding = Column(Vector(1536), nullable=False)

class PR(Base):
    __tablename__ = "prs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    github_pr_id = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    head_sha = Column(String, nullable=False)
    base_sha = Column(String, nullable=False)
    status = Column(
        Enum("pending", "running", "reviewed", "failed", name="pr_status_enum"),
        nullable=False,
        default="pending"
    )

class Review(Base):
    __tablename__ = "reviews"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_id = Column(String, ForeignKey("prs.id"), nullable=False)
    summary = Column(Text, nullable=False)
    structured_json = Column(Text, nullable=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    annotations = relationship("ReviewAnnotation", back_populates="review")

class ReviewAnnotation(Base):
    __tablename__ = "review_annotations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String, ForeignKey("reviews.id"), nullable=False)
    file_path = Column(String, nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)
    severity = Column(
        Enum("high", "medium", "low", name="severity_enum"),
        nullable=False
    )
    category = Column(String, nullable=False)        # "performance", "security", etc.

# Deferred: v1 tracks ingest on Repo (ingest_status + files_ingested).
# Reintroduce when you need job history / concurrent re-ingests.
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    status = Column(
        Enum("pending", "running", "complete", "failed", name="job_status_enum"),
        nullable=False,
        default="pending"
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    files_ingested = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

# v2 — create now, wire up later
class AcceptedPR(Base):
    __tablename__ = "accepted_prs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    diff = Column(Text, nullable=False)
    review_summary = Column(Text, nullable=False)
    merged_at = Column(DateTime, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
