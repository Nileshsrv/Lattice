from sqlalchemy.orm import Session

from .models import ActivityEvent


def record(db: Session, project_id: str, user_id: str | None, kind: str, payload: dict) -> None:
    db.add(ActivityEvent(project_id=project_id, user_id=user_id, kind=kind, payload=payload))
