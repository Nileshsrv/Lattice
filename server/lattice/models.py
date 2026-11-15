import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    research_question: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


ROLES = ("owner", "editor", "collaborator", "reviewer", "viewer")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


PROVENANCE_LABELS = ("measured", "calculated", "simulated", "estimated", "ai-suggested")
ARTIFACT_TYPES = ("dataset", "run", "notebook", "report")


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(Integer, default=1)
    provenance_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    review_state: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


EDGE_KINDS = ("derived-from", "produced-by", "input-to", "cites", "anchors-to")


class ArtifactEdge(Base):
    __tablename__ = "artifact_edges"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    from_artifact: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    to_artifact: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))


class Dataset(Base):
    __tablename__ = "datasets"
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(20))
    columns: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    unknowns: Mapped[list] = mapped_column(JSON, default=list)
    parent_dataset: Mapped[str | None] = mapped_column(ForeignKey("datasets.artifact_id"), nullable=True)
    processing_step: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    artifact: Mapped[Artifact] = relationship()


RUN_STATUSES = ("queued", "running", "completed", "failed", "cancelled")


class Run(Base):
    __tablename__ = "runs"
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(100), index=True)
    tool_version: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_name: Mapped[str] = mapped_column(String(200), default="")
    method: Mapped[dict] = mapped_column(JSON, default=dict)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    input_artifacts: Mapped[dict] = mapped_column(JSON, default=dict)
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    environment: Mapped[dict] = mapped_column(JSON, default=dict)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    arrays: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    guards: Mapped[list] = mapped_column(JSON, default=list)
    parent_run: Mapped[str | None] = mapped_column(ForeignKey("runs.artifact_id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    artifact: Mapped[Artifact] = relationship()


class Notebook(Base):
    __tablename__ = "notebooks"
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))

    artifact: Mapped[Artifact] = relationship()


BLOCK_TYPES = ("text", "heading", "figure")


class Block(Base):
    __tablename__ = "blocks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.artifact_id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class Report(Base):
    __tablename__ = "reports"
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    notebook_id: Mapped[str | None] = mapped_column(ForeignKey("notebooks.artifact_id"), nullable=True)

    artifact: Mapped[Artifact] = relationship()


class ReportVersion(Base):
    __tablename__ = "report_versions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.artifact_id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    html_sha256: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
