from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..deps import SESSION_COOKIE, current_user
from ..models import AuthSession, User
from ..security import hash_password, new_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)


def _start_session(db: Session, response: Response, user: User) -> None:
    token = new_token()
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=config.SESSION_TTL_HOURS),
        )
    )
    db.commit()
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=config.SESSION_TTL_HOURS * 3600
    )


@router.post("/register")
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == body.username).one_or_none()
    if existing is not None:
        raise HTTPException(409, "username already exists")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    _start_session(db, response, user)
    return {"id": user.id, "username": user.username}


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid username or password")
    _start_session(db, response, user)
    return {"id": user.id, "username": user.username}


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username}
