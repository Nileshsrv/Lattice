from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import ActivityEvent, Artifact, Member, Project, ROLES, User

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    research_question: str = ""
    description: str = ""


class MemberAdd(BaseModel):
    username: str
    role: str


@router.post("")
def create_project(
    body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    project = Project(
        name=body.name,
        research_question=body.research_question,
        description=body.description,
        created_by=user.id,
    )
    db.add(project)
    db.flush()
    db.add(Member(project_id=project.id, user_id=user.id, role="owner"))
    record(db, project.id, user.id, "project.created", {"name": project.name})
    db.commit()
    return {"id": project.id, "name": project.name}


@router.get("")
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (
        db.query(Project, Member.role)
        .join(Member, Member.project_id == Project.id)
        .filter(Member.user_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "research_question": p.research_question,
            "role": role,
            "created_at": p.created_at.isoformat(),
        }
        for p, role in rows
    ]


@router.get("/{project_id}")
def project_overview(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    project, member = require_member(db, project_id, user)
    members = (
        db.query(Member, User.username)
        .join(User, User.id == Member.user_id)
        .filter(Member.project_id == project_id)
        .all()
    )
    counts = dict(
        db.query(Artifact.type, func.count(Artifact.id))
        .filter(Artifact.project_id == project_id)
        .group_by(Artifact.type)
        .all()
    )
    activity = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.project_id == project_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "id": project.id,
        "name": project.name,
        "research_question": project.research_question,
        "description": project.description,
        "my_role": member.role,
        "members": [{"username": username, "role": m.role} for m, username in members],
        "artifact_counts": counts,
        "recent_activity": [
            {"kind": a.kind, "payload": a.payload, "at": a.created_at.isoformat()}
            for a in activity
        ],
    }


@router.post("/{project_id}/members")
def add_member(
    project_id: str,
    body: MemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=("owner",))
    if body.role not in ROLES:
        raise HTTPException(422, f"role must be one of {ROLES}")
    target = db.query(User).filter(User.username == body.username).one_or_none()
    if target is None:
        raise HTTPException(404, "no such user")
    existing = (
        db.query(Member)
        .filter(Member.project_id == project_id, Member.user_id == target.id)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(409, "already a member")
    db.add(Member(project_id=project_id, user_id=target.id, role=body.role))
    record(db, project_id, user.id, "member.added", {"username": body.username, "role": body.role})
    db.commit()
    return {"ok": True}
