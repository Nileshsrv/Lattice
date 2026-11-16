from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, Comment, Member, User

router = APIRouter(tags=["comments"])


def _serialize(c: Comment) -> dict:
    return {
        "id": c.id,
        "project_id": c.project_id,
        "artifact_id": c.artifact_id,
        "artifact_version": c.artifact_version,
        "author_id": c.author_id,
        "anchor": c.anchor,
        "text": c.text,
        "created_at": c.created_at.isoformat(),
        "resolved": c.resolved,
        "resolved_by": c.resolved_by,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
    }


class CommentCreate(BaseModel):
    text: str
    anchor: Any = None


class CommentPatch(BaseModel):
    resolved: bool | None = None
    text: str | None = None


@router.post("/api/artifacts/{artifact_id}/comments")
def create_comment(
    artifact_id: str,
    body: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "artifact not found")
    require_member(db, artifact.project_id, user)
    comment = Comment(
        project_id=artifact.project_id,
        artifact_id=artifact_id,
        artifact_version=artifact.version,
        author_id=user.id,
        anchor=body.anchor,
        text=body.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _serialize(comment)


@router.get("/api/artifacts/{artifact_id}/comments")
def list_artifact_comments(
    artifact_id: str,
    include_resolved: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "artifact not found")
    require_member(db, artifact.project_id, user)
    q = db.query(Comment).filter(Comment.artifact_id == artifact_id)
    if not include_resolved:
        q = q.filter(Comment.resolved == False)  # noqa: E712
    comments = q.order_by(Comment.created_at).all()
    return [_serialize(c) for c in comments]


@router.get("/api/projects/{project_id}/comments")
def list_project_comments(
    project_id: str,
    include_resolved: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user)
    q = db.query(Comment).filter(Comment.project_id == project_id)
    if not include_resolved:
        q = q.filter(Comment.resolved == False)  # noqa: E712
    comments = q.order_by(Comment.created_at).all()
    return [_serialize(c) for c in comments]


@router.patch("/api/comments/{comment_id}")
def patch_comment(
    comment_id: str,
    body: CommentPatch,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(404, "comment not found")
    # Verify user is a project member
    _, member = require_member(db, comment.project_id, user)

    if body.text is not None:
        # Only the author can edit text
        if comment.author_id != user.id:
            raise HTTPException(403, "only the author can edit comment text")
        comment.text = body.text

    if body.resolved is not None:
        # Author or owner/editor can resolve
        can_resolve = (
            comment.author_id == user.id or member.role in ("owner", "editor")
        )
        if not can_resolve:
            raise HTTPException(403, "only the author, owner, or editor can resolve comments")
        comment.resolved = body.resolved
        if body.resolved:
            comment.resolved_by = user.id
            comment.resolved_at = datetime.now(timezone.utc)
        else:
            comment.resolved_by = None
            comment.resolved_at = None

    db.commit()
    db.refresh(comment)
    return _serialize(comment)
