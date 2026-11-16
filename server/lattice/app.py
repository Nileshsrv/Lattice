from fastapi import FastAPI, WebSocket

from . import config, ws
from .db import Base, engine
from .routes import assistant, auth, comments, comparisons, datasets, notebooks, projects, reports, review, runs, tools


def create_app() -> FastAPI:
    config.ensure_dirs()
    # Schema management: create_all is used at app start for the slice; Alembic
    # owns migrations from the first schema change onward (see migrations/).
    Base.metadata.create_all(engine)
    app = FastAPI(title="Lattice", version="0.1.0")
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(datasets.router)
    app.include_router(tools.router)
    app.include_router(runs.router)
    app.include_router(comparisons.router)
    app.include_router(notebooks.router)
    app.include_router(reports.router)
    app.include_router(comments.router)
    app.include_router(review.router)
    app.include_router(assistant.router)

    @app.websocket("/api/ws/projects/{project_id}")
    async def project_presence(websocket: WebSocket, project_id: str):
        await ws.presence_endpoint(websocket, project_id)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": "0.1.0"}

    return app


app = create_app()
