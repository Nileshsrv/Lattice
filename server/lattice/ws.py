"""Presence over WebSocket (Stage 5; architecture §4 — facts, not co-editing).

One channel per project. Joining and leaving broadcast the current member
presence list. Extraction seam #2: this hub moves to a dedicated sync server
when Phase 2 CRDT lands.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

from .db import SessionLocal
from .deps import SESSION_COOKIE
from .models import AuthSession, Member, User


class PresenceHub:
    def __init__(self) -> None:
        # project_id -> {username: set of sockets}
        self._rooms: dict[str, dict[str, set[WebSocket]]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def join(self, project_id: str, username: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[project_id].setdefault(username, set()).add(ws)
        await self._broadcast(project_id)

    async def leave(self, project_id: str, username: str, ws: WebSocket) -> None:
        async with self._lock:
            sockets = self._rooms.get(project_id, {}).get(username)
            if sockets is not None:
                sockets.discard(ws)
                if not sockets:
                    self._rooms[project_id].pop(username, None)
            if not self._rooms.get(project_id):
                self._rooms.pop(project_id, None)
        await self._broadcast(project_id)

    async def _broadcast(self, project_id: str) -> None:
        async with self._lock:
            room = self._rooms.get(project_id, {})
            users = sorted(room.keys())
            targets = [ws for sockets in room.values() for ws in sockets]
        message = {"type": "presence", "users": users}
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                pass  # a dead socket is cleaned up by its own leave()


hub = PresenceHub()


def _authenticate(ws: WebSocket, project_id: str) -> str | None:
    """Return the username if the socket's session cookie is a project member."""
    token = ws.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    db = SessionLocal()
    try:
        session = db.get(AuthSession, token)
        if session is None:
            return None
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
        member = (
            db.query(Member)
            .filter(Member.project_id == project_id, Member.user_id == session.user_id)
            .one_or_none()
        )
        if member is None:
            return None
        user = db.get(User, session.user_id)
        return user.username if user else None
    finally:
        db.close()


async def presence_endpoint(ws: WebSocket, project_id: str) -> None:
    username = _authenticate(ws, project_id)
    if username is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    await hub.join(project_id, username, ws)
    try:
        while True:
            await ws.receive_text()  # heartbeats/no-ops keep the socket alive
    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave(project_id, username, ws)
