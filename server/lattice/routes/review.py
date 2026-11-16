"""Review state transition endpoint (A-12)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, User

router = APIRouter(prefix="/api", tags=["review"])

VALID_STATES = ("draft", "needs-review", "approved", "archived")
# Roles that can set approved / archived
APPROVER_ROLES = ("reviewer", "editor", "owner")


class ReviewUpdate(BaseModel):
    state: str


@router.patch("/artifacts/{artifact_id}/review")
def update_review_state(
    artifact_id: str,
    body: ReviewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if body.state not in VALID_STATES:
        raise HTTPException(422, f"invalid state; must be one of {VALID_STATES}")

    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(404, "artifact not found")

    # Confirm user is a member; get their role
    _project, member = require_member(db, artifact.project_id, user)

    if body.state in ("approved", "archived") and member.role not in APPROVER_ROLES:
        raise HTTPException(403, f"requires role: {', '.join(APPROVER_ROLES)}")

    old_state = artifact.review_state
    artifact.review_state = body.state

    now = datetime.now(timezone.utc)
    record(
        db,
        artifact.project_id,
        user.id,
        "review_state_changed",
        {
            "artifact_id": artifact_id,
            "old_state": old_state,
            "new_state": body.state,
            "actor_id": user.id,
            "timestamp": now.isoformat(),
        },
    )
    db.commit()

    # Human review decision recorded.
    return {
        "artifact_id": artifact_id,
        "new_state": body.state,
        "actor": user.username,
        "timestamp": now.isoformat(),
        "message": "Human review decision recorded.",
    }
