from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, BLOCK_TYPES, Block, Notebook, Run, User

router = APIRouter(prefix="/api", tags=["notebooks"])

WRITER_ROLES = ("owner", "editor", "collaborator")


class NotebookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class BlockCreate(BaseModel):
    type: str
    content: dict = Field(default_factory=dict)
    position: int | None = None


class BlockUpdate(BaseModel):
    content: dict
    revision: int


def _validate_block(db: Session, project_id: str, body_type: str, content: dict) -> None:
    if body_type not in BLOCK_TYPES:
        raise HTTPException(422, f"block type must be one of {BLOCK_TYPES}")
    if body_type == "figure":
        run_id = content.get("run_artifact_id")
        if not run_id:
            raise HTTPException(422, "figure blocks must reference run_artifact_id")
        artifact = db.get(Artifact, run_id)
        run = db.get(Run, run_id)
        if artifact is None or run is None or artifact.project_id != project_id:
            raise HTTPException(422, "figure references a run that is not in this project")
        content.setdefault("run_version", artifact.version)
        if content.get("array") and content["array"] not in run.arrays:
            raise HTTPException(422, f"run has no array '{content['array']}'")


@router.post("/projects/{project_id}/notebooks")
def create_notebook(
    project_id: str,
    body: NotebookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)
    artifact = Artifact(
        project_id=project_id, type="notebook", name=body.title, created_by=user.id
    )
    db.add(artifact)
    db.flush()
    db.add(Notebook(artifact_id=artifact.id, title=body.title))
    record(db, project_id, user.id, "notebook.created", {"artifact_id": artifact.id})
    db.commit()
    return {"artifact_id": artifact.id, "title": body.title}


def _get_notebook(db: Session, user: User, notebook_id: str) -> tuple[Artifact, Notebook]:
    artifact = db.get(Artifact, notebook_id)
    if artifact is None or artifact.type != "notebook":
        raise HTTPException(404, "notebook not found")
    require_member(db, artifact.project_id, user)
    return artifact, db.get(Notebook, notebook_id)


@router.get("/projects/{project_id}/notebooks")
def list_notebooks(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    require_member(db, project_id, user)
    rows = (
        db.query(Artifact, Notebook)
        .join(Notebook, Notebook.artifact_id == Artifact.id)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [{"artifact_id": a.id, "title": n.title, "version": a.version} for a, n in rows]


@router.get("/notebooks/{notebook_id}")
def notebook_detail(
    notebook_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    artifact, notebook = _get_notebook(db, user, notebook_id)
    blocks = (
        db.query(Block)
        .filter(Block.notebook_id == notebook_id)
        .order_by(Block.position)
        .all()
    )
    return {
        "artifact_id": artifact.id,
        "title": notebook.title,
        "version": artifact.version,
        "project_id": artifact.project_id,
        "blocks": [
            {
                "id": b.id,
                "position": b.position,
                "type": b.type,
                "content": b.content,
                "revision": b.revision,
            }
            for b in blocks
        ],
    }


@router.post("/notebooks/{notebook_id}/blocks")
def add_block(
    notebook_id: str,
    body: BlockCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    artifact, _notebook = _get_notebook(db, user, notebook_id)
    require_member(db, artifact.project_id, user, roles=WRITER_ROLES)
    _validate_block(db, artifact.project_id, body.type, body.content)
    if body.position is None:
        max_pos = (
            db.query(func.max(Block.position)).filter(Block.notebook_id == notebook_id).scalar()
        )
        position = (max_pos or 0) + 1
    else:
        position = body.position
    block = Block(notebook_id=notebook_id, position=position, type=body.type, content=body.content)
    db.add(block)
    artifact.version += 1
    db.commit()
    return {"id": block.id, "position": position, "revision": block.revision}


@router.patch("/blocks/{block_id}")
def update_block(
    block_id: str,
    body: BlockUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    block = db.get(Block, block_id)
    if block is None:
        raise HTTPException(404, "block not found")
    artifact, _notebook = _get_notebook(db, user, block.notebook_id)
    require_member(db, artifact.project_id, user, roles=WRITER_ROLES)
    if body.revision != block.revision:
        # I-8: the losing edit is surfaced with the server copy, never silently applied.
        raise HTTPException(
            409,
            detail={
                "message": "block was edited by someone else",
                "server_revision": block.revision,
                "server_content": block.content,
            },
        )
    _validate_block(db, artifact.project_id, block.type, body.content)
    block.content = body.content
    block.revision += 1
    artifact.version += 1
    db.commit()
    return {"id": block.id, "revision": block.revision}
