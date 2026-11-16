"""AI Research Assistant endpoints (Stage 5).

Rule-based dispatcher — NO external LLM API calls.
All physics numbers come from tool execution only; text responses never assert values.
All outputs carry provenance_label="ai-suggested".
"""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, Dataset, Member, Project, Run, User
from ..runs.orchestrator import RunTimeout, get_orchestrator
from ..store import objects
from ..tools import registry
from ..tools.contract import InputValidationError, convert_and_validate

router = APIRouter(prefix="/api", tags=["assistant"])

WRITER_ROLES = ("owner", "editor", "collaborator")

# ---------------------------------------------------------------------------
# Keyword → tool mapping (rule-based; order matters — more specific first)
# ---------------------------------------------------------------------------
_KEYWORD_TOOL_MAP = [
    # (keywords_any_of, tool_id, description)
    (["compton", "scatter"], "compton.scattering", "Compton Scattering Lab"),
    (["tunnel", "barrier"], "quantum.rectangular_tunneling", "Quantum Tunnelling Lab"),
    (["sweep"], "quantum.rectangular_tunneling_sweep", "Quantum Tunnelling Energy Sweep"),
    (["wien", "peak wavelength", "displacement"], "stellar.wien_temperature", "Wien's Displacement Law Calculator"),
    (["blackbody", "stellar", "star", "spectrum", "spectral", "temperature"], "stellar.blackbody_fit", "Blackbody Continuum Fit"),
    (["gaussian", "peak fit"], "analysis.gaussian_peak_fit", "Gaussian Peak Fit"),
    (["propagat", "uncertainty"], "analysis.independent_error_propagation", "Error Propagation"),
    (["fit", "regression", "analysis", "slope"], "analysis.linear_regression", "Linear Regression"),
]


def _detect_tool(message: str) -> tuple[str, str] | None:
    """Return (tool_id, description) if a keyword match is found, else None."""
    lower = message.lower()
    for keywords, tool_id, description in _KEYWORD_TOOL_MAP:
        if any(kw in lower for kw in keywords):
            # Confirm tool exists in registry; fall through on KeyError
            try:
                registry.get(tool_id)
                return tool_id, description
            except KeyError:
                continue
    return None


def _build_text_response(message: str, tool_id: str | None, description: str | None) -> str:
    """Build a natural-language response that never asserts physics values."""
    if tool_id is None:
        return (
            "I can help you run physics and analysis tools on your project data. "
            "Try asking about Compton scattering, quantum tunneling, stellar blackbody "
            "analysis, or data fitting/regression. I'll suggest a tool plan for your approval "
            "before anything is executed."
        )
    return (
        f"I can help you run the **{description}** tool (`{tool_id}`). "
        "I've prepared a tool plan below — please review the suggested parameters "
        "and approve execution when you're ready. No physics values will be computed "
        "until you approve."
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AssistantContext(BaseModel):
    run_ids: list[str] = Field(default_factory=list)
    dataset_ids: list[str] = Field(default_factory=list)


class AssistantRequest(BaseModel):
    message: str
    context: AssistantContext = Field(default_factory=AssistantContext)


class ExecuteRequest(BaseModel):
    tool_plan: dict[str, Any]
    approved: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/assistant")
def assistant_query(
    project_id: str,
    body: AssistantRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    project, _member = require_member(db, project_id, user)

    # a. Load project summary
    member_count = (
        db.query(Member).filter(Member.project_id == project_id).count()
    )
    recent_runs = (
        db.query(Artifact, Run)
        .join(Run, Run.artifact_id == Artifact.id)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
        .limit(5)
        .all()
    )
    dataset_artifacts = (
        db.query(Artifact)
        .filter(Artifact.project_id == project_id, Artifact.type == "dataset")
        .all()
    )

    # b. Parse message for tool keywords
    tool_match = _detect_tool(body.message)
    tool_id: str | None = None
    tool_description: str | None = None
    if tool_match:
        tool_id, tool_description = tool_match

    # c. Build tool_plan. Tools that take a dataset are linked, not executed,
    # because assistant execution binds no data (the tool page does that flow).
    tool_plan = None
    if tool_id:
        contract, _fn = registry.get(tool_id)
        tool_plan = {
            "tool_name": tool_id,
            "tool_label": contract.name,
            "maturity": contract.maturity,
            "inputs": [
                {
                    "name": s.name,
                    "label": s.label,
                    "canonical_unit": s.canonical_unit,
                    "default": s.default,
                    "required": s.required,
                }
                for s in contract.inputs
            ],
            "needs_dataset": bool(contract.dataset_inputs),
            "guards": contract.guards,
            "suggested_params": {},
            "requires_user_approval": True,
        }

    # d. Build citations for context artifacts
    citations: list[dict] = []
    for run_id in body.context.run_ids:
        artifact = db.get(Artifact, run_id)
        if artifact and artifact.project_id == project_id:
            citations.append({
                "artifact_id": artifact.id,
                "name": artifact.name,
                "type": artifact.type,
            })
    for ds_id in body.context.dataset_ids:
        artifact = db.get(Artifact, ds_id)
        if artifact and artifact.project_id == project_id:
            citations.append({
                "artifact_id": artifact.id,
                "name": artifact.name,
                "type": artifact.type,
            })

    # e. Build response — text must never assert physics values
    text = _build_text_response(body.message, tool_id, tool_description)

    return {
        "text": text,
        "tool_plan": tool_plan,
        "citations": citations,
        "provenance_label": "ai-suggested",
        "context_summary": {
            "project_name": project.name,
            "recent_run_count": len(recent_runs),
            "dataset_count": len(dataset_artifacts),
        },
    }


@router.post("/projects/{project_id}/assistant/execute")
def assistant_execute(
    project_id: str,
    body: ExecuteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)

    if not body.approved:
        return {"status": "cancelled"}

    tool_plan = body.tool_plan
    tool_name = tool_plan.get("tool_name") or tool_plan.get("tool_id")
    if not tool_name:
        raise HTTPException(422, "tool_plan must include 'tool_name'")

    params_raw: dict = tool_plan.get("params", {})

    # Resolve the tool from registry
    try:
        contract, _fn = registry.get(tool_name)
    except KeyError:
        raise HTTPException(404, f"unknown tool: {tool_name}")
    if contract.dataset_inputs:
        raise HTTPException(
            422,
            f"tool {tool_name} requires a dataset; run it from its tool page "
            "where data is bound by reference",
        )

    # Convert and validate inputs (params_raw must be {name: {value, unit}} format)
    try:
        params = convert_and_validate(contract, params_raw)
    except InputValidationError as exc:
        raise HTTPException(422, detail={"input_errors": exc.errors})

    # Create the Run artifact (mirror routes/runs.py flow; mark as ai-suggested)
    run_artifact = Artifact(
        project_id=project_id,
        type="run",
        name=f"{contract.name} run (AI-suggested)",
        provenance_label="ai-suggested",
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
            name: {
                "value": value,
                "unit": next(
                    s.canonical_unit for s in contract.inputs if s.name == name
                ),
            }
            for name, value in params.items()
        },
        input_artifacts={},
        assumptions=contract.model.assumptions,
        guards=contract.guards,
        parent_run=None,
    )
    db.add(run)
    db.commit()

    # Execute via orchestrator (no external LLM; pure physics tool)
    try:
        payload = get_orchestrator().execute(
            contract.id, contract.category, params, {}
        )
    except RunTimeout as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(500, f"run failed: {exc}")
    except Exception as exc:
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

    record(
        db,
        project_id,
        user.id,
        "run.completed",
        {"artifact_id": run_artifact.id, "tool_id": contract.id, "provenance": "ai-suggested"},
    )
    db.commit()

    return {
        "status": "executed",
        "run_id": run_artifact.id,
        "result": {
            "outputs": run.outputs,
            "warnings": run.warnings,
            "checks": run.checks,
        },
    }
