from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector
import uuid

from core.config import settings

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
    user = relationship("User", back_populates="repos")

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
    embedding = Column(Vector(settings.embedding_dimensions), nullable=False)

class CodeDependency(Base):
    __tablename__ = "code_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "repo_id",
            "from_file",
            "to_file",
            "edge_type",
            name="uq_code_dependencies_edge",
        ),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id"), nullable=False)
    from_file = Column(String, nullable=False)
    to_file = Column(String, nullable=True)  # null when edge_type = external
    edge_type = Column(
        Enum("import", "reexport", "external", name="dependency_edge_type_enum"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False)

class PR(Base):
    __tablename__ = "prs"
    __table_args__ = (
        UniqueConstraint("repo_id", "number", name="uq_prs_repo_number"),
    )
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
    __table_args__ = (
        UniqueConstraint("pr_id", "head_sha", name="uq_reviews_pr_head_sha"),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pr_id = Column(String, ForeignKey("prs.id"), nullable=False)
    head_sha = Column(String, nullable=False)
    status = Column(
        Enum(
            "pending",
            "running",
            "complete",
            "error",
            name="review_status_enum",
        ),
        nullable=False,
        default="pending",
    )
    summary = Column(Text, nullable=True)
    structured_json = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
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
    review = relationship("Review", back_populates="annotations")

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
    embedding = Column(Vector(settings.embedding_dimensions), nullable=True)
