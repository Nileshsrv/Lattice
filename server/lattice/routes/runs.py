import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..activity import record
from ..datasets.ingest import column_in_canonical_unit, parse_csv
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, ArtifactEdge, Dataset, Run, User
from ..runs.orchestrator import RunTimeout, get_orchestrator
from ..store import objects
from ..tools import registry
from ..tools.contract import InputValidationError, convert_and_validate

router = APIRouter(prefix="/api", tags=["runs"])

WRITER_ROLES = ("owner", "editor", "collaborator")


class RunCreate(BaseModel):
    tool_id: str
    # {input_name: {"value": number, "unit": str}}
    inputs: dict[str, dict] = Field(default_factory=dict)
    # {dataset_input_name: dataset artifact id}
    datasets: dict[str, str] = Field(default_factory=dict)
    parent_run: str | None = None
    name: str | None = None


def _run_json(artifact: Artifact, run: Run) -> dict:
    return {
        "artifact_id": artifact.id,
        "name": artifact.name,
        "version": artifact.version,
        "provenance_label": artifact.provenance_label,
        "tool_id": run.tool_id,
        "tool_version": run.tool_version,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "model_name": run.model_name,
        "method": run.method,
        "inputs": run.inputs,
        "input_artifacts": run.input_artifacts,
        "assumptions": run.assumptions,
        "environment": run.environment,
        "seed": run.seed,
        "outputs": run.outputs,
        "arrays": run.arrays,
        "warnings": run.warnings,
        "checks": run.checks,
        "guards": run.guards,
        "parent_run": run.parent_run,
        "error": run.error,
    }


@router.post("/projects/{project_id}/runs")
def create_run(
    project_id: str,
    body: RunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)
    try:
        contract, _fn = registry.get(body.tool_id)
    except KeyError:
        raise HTTPException(404, f"unknown tool: {body.tool_id}")

    try:
        params = convert_and_validate(contract, body.inputs)
    except InputValidationError as exc:
        raise HTTPException(422, detail={"input_errors": exc.errors})

    if body.parent_run is not None:
        parent = db.get(Run, body.parent_run)
        if parent is None or parent.artifact.project_id != project_id:
            raise HTTPException(422, "parent_run does not exist in this project")

    # Resolve dataset bindings by reference; record resolved hashes (the bus).
    data_payload: dict[str, dict] = {}
    input_artifacts: dict[str, dict] = {}
    for spec in contract.dataset_inputs:
        artifact_ref = body.datasets.get(spec.name)
        if artifact_ref is None:
            raise HTTPException(422, f"dataset input '{spec.name}' is required")
        ds_artifact = db.get(Artifact, artifact_ref)
        if ds_artifact is None or ds_artifact.type != "dataset" or ds_artifact.project_id != project_id:
            raise HTTPException(422, f"'{spec.name}': no such dataset in this project")
        dataset = db.get(Dataset, artifact_ref)
        parsed = parse_csv(objects.get(dataset.sha256))
        columns: dict[str, list[float]] = {}
        for col in spec.required_columns:
            try:
                columns[col["name"]] = column_in_canonical_unit(
                    parsed, col["name"], col["canonical_unit"]
                )
            except ValueError as exc:
                raise HTTPException(422, f"'{spec.name}': {exc}")
        data_payload[spec.name] = columns
        input_artifacts[spec.name] = {
            "artifact_id": ds_artifact.id,
            "version": ds_artifact.version,
            "sha256": dataset.sha256,
            "provenance_label": ds_artifact.provenance_label,
            "unknowns": dataset.unknowns,
        }

    run_artifact = Artifact(
        project_id=project_id,
        type="run",
        name=body.name or f"{contract.name} run",
        provenance_label="calculated",
        created_by=user.id,
    )
    db.add(run_artifact)
    db.flush()
    run = Run(
        artifact_id=run_artifact.id,
        tool_id=contract.id,
        tool_version=contract.version,
        status="running",
        started_at=datetime.now(timezone.utc),
        model_name=contract.model.name,
        method=contract.method.model_dump(),
        inputs={
            name: {"value": value, "unit": next(
                s.canonical_unit for s in contract.inputs if s.name == name
            )}
            for name, value in params.items()
        },
        input_artifacts=input_artifacts,
        assumptions=contract.model.assumptions,
        guards=contract.guards,
        parent_run=body.parent_run,
    )
    db.add(run)
    db.commit()

    try:
        payload = get_orchestrator().execute(
            contract.id, contract.category, params, data_payload
        )
    except RunTimeout as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(500, f"run failed: {exc}")
    except Exception as exc:  # worker raised: keep the failed run with its log (A-4)
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(422, f"run failed: {exc}")

    result = payload["result"]
    array_refs: dict[str, dict] = {}
    for array_name, array in result["arrays"].items():
        content = json.dumps(array, separators=(",", ":")).encode()
        array_refs[array_name] = {"sha256": objects.put(content), "format": "json"}

    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    run.environment = payload["environment"]
    run.outputs = result["scalars"]
    run.arrays = array_refs
    run.warnings = result["warnings"]
    run.checks = result["checks"]

    for binding in input_artifacts.values():
        db.add(
            ArtifactEdge(
                from_artifact=binding["artifact_id"],
                to_artifact=run_artifact.id,
                kind="input-to",
            )
        )
    record(
        db,
        project_id,
        user.id,
        "run.completed",
        {"artifact_id": run_artifact.id, "tool_id": contract.id},
    )
    db.commit()
    return _run_json(run_artifact, run)


def _get_run(db: Session, user: User, artifact_id: str) -> tuple[Artifact, Run]:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or artifact.type != "run":
        raise HTTPException(404, "run not found")
    require_member(db, artifact.project_id, user)
    run = db.get(Run, artifact_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return artifact, run


@router.get("/projects/{project_id}/runs")
def list_runs(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    require_member(db, project_id, user)
    rows = (
        db.query(Artifact, Run)
        .join(Run, Run.artifact_id == Artifact.id)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [_run_json(a, r) for a, r in rows]


@router.get("/runs/{artifact_id}")
def run_detail(
    artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    artifact, run = _get_run(db, user, artifact_id)
    return _run_json(artifact, run)


@router.get("/runs/{artifact_id}/arrays/{array_name}")
def run_array(
    artifact_id: str,
    array_name: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _artifact, run = _get_run(db, user, artifact_id)
    ref = run.arrays.get(array_name)
    if ref is None:
        raise HTTPException(404, f"run has no array '{array_name}'")
    return json.loads(objects.get(ref["sha256"]))
