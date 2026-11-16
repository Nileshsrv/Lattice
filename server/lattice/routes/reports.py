from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..activity import record
from ..db import get_db
from ..deps import current_user, require_member
from ..models import Artifact, Notebook, Report, ReportVersion, Run, User
from ..reports.builder import build_html
from ..reports.pdf import render_pdf
from ..store import objects

router = APIRouter(prefix="/api", tags=["reports"])

WRITER_ROLES = ("owner", "editor", "collaborator")


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notebook_id: str
    report_type: str = "lab-report"


@router.post("/projects/{project_id}/reports")
def create_report(
    project_id: str,
    body: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_member(db, project_id, user, roles=WRITER_ROLES)
    nb_artifact = db.get(Artifact, body.notebook_id)
    if nb_artifact is None or nb_artifact.type != "notebook" or nb_artifact.project_id != project_id:
        raise HTTPException(422, "notebook not found in this project")
    artifact = Artifact(project_id=project_id, type="report", name=body.title, created_by=user.id)
    db.add(artifact)
    db.flush()
    db.add(Report(artifact_id=artifact.id, title=body.title, notebook_id=body.notebook_id, report_type=body.report_type))
    record(db, project_id, user.id, "report.created", {"artifact_id": artifact.id})
    db.commit()
    return {"artifact_id": artifact.id, "title": body.title, "report_type": body.report_type}


@router.get("/projects/{project_id}/reports")
def list_reports(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    require_member(db, project_id, user)
    rows = (
        db.query(Artifact, Report)
        .join(Report, Report.artifact_id == Artifact.id)
        .filter(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [
        {
            "artifact_id": a.id,
            "title": r.title,
            "notebook_id": r.notebook_id,
            "report_type": r.report_type,
            "version": a.version,
        }
        for a, r in rows
    ]


def _get_report(db: Session, user: User, report_id: str) -> tuple[Artifact, Report]:
    artifact = db.get(Artifact, report_id)
    if artifact is None or artifact.type != "report":
        raise HTTPException(404, "report not found")
    require_member(db, artifact.project_id, user)
    return artifact, db.get(Report, report_id)


@router.post("/reports/{report_id}/export")
def export_report(
    report_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    artifact, report = _get_report(db, user, report_id)
    require_member(db, artifact.project_id, user, roles=WRITER_ROLES)
    notebook = db.get(Notebook, report.notebook_id)
    if notebook is None:
        raise HTTPException(422, "the report's notebook no longer exists")
    from ..models import Project

    project = db.get(Project, artifact.project_id)
    html, manifest = build_html(db, project, notebook, report.title)
    sha = objects.put(html.encode())
    number = (
        db.query(func.max(ReportVersion.number))
        .filter(ReportVersion.report_id == report_id)
        .scalar()
        or 0
    ) + 1
    version = ReportVersion(
        report_id=report_id, number=number, html_sha256=sha, manifest=manifest
    )
    db.add(version)
    artifact.version = number
    record(
        db,
        artifact.project_id,
        user.id,
        "report.exported",
        {"artifact_id": report_id, "version": number},
    )
    db.commit()
    return {"report_id": report_id, "version": number, "html_sha256": sha, "manifest": manifest}


@router.get("/reports/{report_id}")
def report_detail(
    report_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    artifact, report = _get_report(db, user, report_id)
    versions = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.number)
        .all()
    )
    return {
        "artifact_id": artifact.id,
        "title": report.title,
        "notebook_id": report.notebook_id,
        "report_type": report.report_type,
        "versions": [
            {
                "number": v.number,
                "created_at": v.created_at.isoformat(),
                "html_sha256": v.html_sha256,
                "n_artifacts": len(v.manifest.get("artifacts", [])),
            }
            for v in versions
        ],
    }


@router.get("/reports/{report_id}/staleness")
def report_staleness(
    report_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    artifact, report = _get_report(db, user, report_id)
    latest_version = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.number.desc())
        .first()
    )

    if latest_version is None:
        return {
            "report_id": report_id,
            "stale": False,
            "stale_artifacts": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    manifest = latest_version.manifest
    stale_artifacts: list[str] = []

    # Check notebook version
    nb_info = manifest.get("notebook") or {}
    if nb_info.get("artifact_id"):
        nb_art = db.get(Artifact, nb_info["artifact_id"])
        if nb_art and nb_art.version > nb_info.get("version", 1):
            stale_artifacts.append(nb_art.id)

    # Check each artifact in the report manifest
    for entry in manifest.get("artifacts", []):
        art_id = entry.get("artifact_id")
        if not art_id:
            continue
        art = db.get(Artifact, art_id)
        if art is None:
            stale_artifacts.append(art_id)
            continue
        if art.version != entry.get("version"):
            stale_artifacts.append(art_id)
            continue

        # If it's a Run, check if its inputs have changed
        if art.type == "run":
            run = db.get(Run, art_id)
            if run and run.input_artifacts:
                for _input_name, input_meta in run.input_artifacts.items():
                    parent_ds_id = input_meta.get("artifact_id")
                    if parent_ds_id:
                        parent_art = db.get(Artifact, parent_ds_id)
                        if parent_art:
                            # If input dataset was updated or created after the run started
                            if parent_art.version > input_meta.get("version", 1):
                                stale_artifacts.append(art_id)
                                break

    return {
        "report_id": report_id,
        "stale": len(stale_artifacts) > 0,
        "stale_artifacts": list(set(stale_artifacts)),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/reports/{report_id}/versions/{number}/html", response_class=HTMLResponse)
def report_html(
    report_id: str,
    number: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _artifact, _report = _get_report(db, user, report_id)
    version = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id, ReportVersion.number == number)
        .one_or_none()
    )
    if version is None:
        raise HTTPException(404, "no such report version")
    return HTMLResponse(objects.get(version.html_sha256).decode())


@router.get("/reports/{report_id}/versions/{number}/pdf")
def report_pdf(
    report_id: str,
    number: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _artifact, _report = _get_report(db, user, report_id)
    version = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id, ReportVersion.number == number)
        .one_or_none()
    )
    if version is None:
        raise HTTPException(404, "no such report version")
    if version.pdf_sha256 is None:
        # Render once from the frozen HTML, then cache by content hash.
        pdf_bytes = render_pdf(objects.get(version.html_sha256).decode())
        version.pdf_sha256 = objects.put(pdf_bytes)
        db.commit()
    else:
        pdf_bytes = objects.get(version.pdf_sha256)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="report-v{number}.pdf"'
        },
    )


@router.get("/reports/{report_id}/versions/{number}/manifest")
def report_manifest(
    report_id: str,
    number: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _get_report(db, user, report_id)
    version = (
        db.query(ReportVersion)
        .filter(ReportVersion.report_id == report_id, ReportVersion.number == number)
        .one_or_none()
    )
    if version is None:
        raise HTTPException(404, "no such report version")
    return version.manifest
