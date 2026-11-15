import hashlib
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from .. import config
from ..activity import record
from ..datasets.ingest import parse_csv
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, Dataset, PROVENANCE_LABELS, User
from ..store import objects

router = APIRouter(prefix="/api", tags=["datasets"])

WRITER_ROLES = ("owner", "editor", "collaborator")


@router.post("/projects/{project_id}/datasets")
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    license: str = Form(""),
    source_note: str = Form(""),
    provenance_label: str = Form("measured"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)
    if provenance_label not in PROVENANCE_LABELS:
        raise HTTPException(422, f"provenance_label must be one of {PROVENANCE_LABELS}")
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"file is {len(content)} bytes; the MVP upload ceiling is "
            f"{config.MAX_UPLOAD_BYTES} bytes (100 MB)",
        )
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(422, "only CSV uploads are supported in the vertical slice")
    try:
        parsed = parse_csv(content)
    except ValueError as exc:
        raise HTTPException(422, f"could not parse CSV: {exc}")

    sha = objects.put(content)
    unknowns = list(parsed["unknowns"])
    if not license.strip():
        unknowns.append("license/attribution not provided")

    artifact = Artifact(
        project_id=project_id,
        type="dataset",
        name=name,
        provenance_label=provenance_label,
        created_by=user.id,
    )
    db.add(artifact)
    db.flush()
    dataset = Dataset(
        artifact_id=artifact.id,
        sha256=sha,
        size=len(content),
        format="csv",
        columns=parsed["columns"],
        source={
            "filename": file.filename,
            "license": license,
            "note": source_note,
            "quality_flags": parsed["quality_flags"],
            "n_rows": parsed["n_rows"],
        },
        unknowns=unknowns,
    )
    db.add(dataset)
    record(db, project_id, user.id, "dataset.ingested", {"artifact_id": artifact.id, "name": name})
    db.commit()
    return _dataset_json(artifact, dataset)


def _dataset_json(artifact: Artifact, dataset: Dataset) -> dict:
    return {
        "artifact_id": artifact.id,
        "name": artifact.name,
        "version": artifact.version,
        "provenance_label": artifact.provenance_label,
        "sha256": dataset.sha256,
        "size": dataset.size,
        "format": dataset.format,
        "columns": dataset.columns,
        "source": dataset.source,
        "unknowns": dataset.unknowns,
        "created_at": artifact.created_at.isoformat(),
    }


def _get_dataset(db: Session, user: User, artifact_id: str) -> tuple[Artifact, Dataset]:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or artifact.type != "dataset":
        raise HTTPException(404, "dataset not found")
    require_member(db, artifact.project_id, user)
    dataset = db.get(Dataset, artifact_id)
    if dataset is None:
        raise HTTPException(404, "dataset not found")
    return artifact, dataset


@router.get("/projects/{project_id}/datasets")
def list_datasets(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    require_member(db, project_id, user)
    rows = (
        db.query(Artifact, Dataset)
        .join(Dataset, Dataset.artifact_id == Artifact.id)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [_dataset_json(a, d) for a, d in rows]


@router.get("/datasets/{artifact_id}")
def dataset_detail(
    artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    artifact, dataset = _get_dataset(db, user, artifact_id)
    return _dataset_json(artifact, dataset)


@router.get("/datasets/{artifact_id}/preview")
def dataset_preview(
    artifact_id: str,
    limit: int = 2000,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _artifact, dataset = _get_dataset(db, user, artifact_id)
    parsed = parse_csv(objects.get(dataset.sha256))
    data = {k: v[:limit] for k, v in parsed["data"].items()}
    return {"columns": parsed["columns"], "data": data, "n_rows": parsed["n_rows"]}


@router.get("/datasets/{artifact_id}/raw")
def dataset_raw(
    artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    _artifact, dataset = _get_dataset(db, user, artifact_id)
    return Response(content=objects.get(dataset.sha256), media_type="text/csv")


@router.get("/datasets/{artifact_id}/verify")
def dataset_verify(
    artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    _artifact, dataset = _get_dataset(db, user, artifact_id)
    content = objects.get(dataset.sha256)
    actual = hashlib.sha256(content).hexdigest()
    return {"stored_sha256": dataset.sha256, "actual_sha256": actual, "intact": actual == dataset.sha256}
