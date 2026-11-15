from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuthSession, Member, Project, User

SESSION_COOKIE = "lattice_session"


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "not authenticated")
    session = db.get(AuthSession, token)
    if session is None:
        raise HTTPException(401, "invalid session")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(401, "session expired")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "unknown user")
    return user


def require_member(
    db: Session, project_id: str, user: User, roles: tuple[str, ...] | None = None
) -> tuple[Project, Member]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "project not found")
    member = (
        db.query(Member)
        .filter(Member.project_id == project_id, Member.user_id == user.id)
        .one_or_none()
    )
    if member is None:
        # Private by default: non-members learn nothing beyond 404.
        raise HTTPException(404, "project not found")
    if roles is not None and member.role not in roles:
        raise HTTPException(403, f"requires role: {', '.join(roles)}")
    return project, member
