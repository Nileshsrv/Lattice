"""Saved comparisons reference two immutable runs in the same project."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, ArtifactEdge, Run, User

router = APIRouter(prefix="/api", tags=["comparisons"])
WRITER_ROLES = ("owner", "editor", "collaborator")


class ComparisonCreate(BaseModel):
    run_a: str
    run_b: str


def _comparison_json(db: Session, artifact: Artifact) -> dict:
    edges = db.query(ArtifactEdge).filter(
        ArtifactEdge.from_artifact == artifact.id,
        ArtifactEdge.kind.in_(("compares-a", "compares-b")),
    ).all()
    run_ids = {edge.kind: edge.to_artifact for edge in edges}
    if set(run_ids) != {"compares-a", "compares-b"}:
        raise HTTPException(500, "comparison artifact must reference exactly two runs")
    ordered_run_ids = [run_ids["compares-a"], run_ids["compares-b"]]
    entries = []
    for run_id in ordered_run_ids:
        run_artifact = db.get(Artifact, run_id)
        run = db.get(Run, run_id)
        if run_artifact is None or run is None:
            raise HTTPException(404, "a referenced run is no longer available")
        entries.append({
            "artifact_id": run_artifact.id,
            "version": run_artifact.version,
            "name": run_artifact.name,
            "tool_id": run.tool_id,
            "tool_version": run.tool_version,
            "model_name": run.model_name,
            "inputs": run.inputs,
            "outputs": run.outputs,
            "arrays": run.arrays,
        })
    left, right = entries
    param_names = sorted(set(left["inputs"]) | set(right["inputs"]))
    output_names = sorted(set(left["outputs"]) | set(right["outputs"]))
    return {
        "artifact_id": artifact.id,
        "name": artifact.name,
        "version": artifact.version,
        "project_id": artifact.project_id,
        "runs": entries,
        "parameter_diff": {
            key: {"a": left["inputs"].get(key), "b": right["inputs"].get(key), "different": left["inputs"].get(key) != right["inputs"].get(key)}
            for key in param_names
        },
        "output_diff": {
            key: {"a": left["outputs"].get(key), "b": right["outputs"].get(key)}
            for key in output_names
        },
    }


@router.post("/projects/{project_id}/comparisons")
def create_comparison(
    project_id: str,
    body: ComparisonCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)
    if body.run_a == body.run_b:
        raise HTTPException(422, "choose two different runs")
    runs = [db.get(Run, run_id) for run_id in (body.run_a, body.run_b)]
    artifacts = [db.get(Artifact, run_id) for run_id in (body.run_a, body.run_b)]
    if any(run is None or artifact is None or artifact.type != "run" or artifact.project_id != project_id for run, artifact in zip(runs, artifacts)):
        raise HTTPException(422, "both runs must belong to this project")
    if any(run.status != "completed" for run in runs):
        raise HTTPException(422, "only completed runs can be compared")
    comparison = Artifact(
        project_id=project_id,
        type="comparison",
        name=f"Comparison: {artifacts[0].name} ↔ {artifacts[1].name}",
        provenance_label="calculated",
        created_by=user.id,
    )
    db.add(comparison)
    db.flush()
    for run_id, edge_kind in ((body.run_a, "compares-a"), (body.run_b, "compares-b")):
        db.add(ArtifactEdge(from_artifact=comparison.id, to_artifact=run_id, kind=edge_kind))
    record(db, project_id, user.id, "runs.compared", {"artifact_id": comparison.id, "runs": [body.run_a, body.run_b]})
    db.commit()
    return _comparison_json(db, comparison)


@router.get("/comparisons/{comparison_id}")
def comparison_detail(
    comparison_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    artifact = db.get(Artifact, comparison_id)
    if artifact is None or artifact.type != "comparison":
        raise HTTPException(404, "comparison not found")
    require_member(db, artifact.project_id, user)
    return _comparison_json(db, artifact)
