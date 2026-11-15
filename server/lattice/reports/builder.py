"""Report builder: assembles HTML from saved artifacts only (architecture §5).

Every figure and value resolves through artifact references; the export embeds
a manifest of artifact@version + content hashes (I-10). Figures are rendered
client-side by Plotly from the run's stored arrays embedded as JSON — the same
data path the app uses. PDF capture of this HTML arrives with Playwright in
Stage 4 (docs/stage3 limitations).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from ..models import Artifact, Block, Dataset, Notebook, Project, Run
from ..store import objects

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def build_html(db: Session, project: Project, notebook: Notebook, title: str) -> tuple[str, dict]:
    blocks = (
        db.query(Block)
        .filter(Block.notebook_id == notebook.artifact_id)
        .order_by(Block.position)
        .all()
    )

    sections: list[dict] = []
    manifest_entries: dict[str, dict] = {}
    limitations: list[str] = []
    seen_limitations: set[str] = set()

    def add_limitation(text: str) -> None:
        if text not in seen_limitations:
            seen_limitations.add(text)
            limitations.append(text)

    def add_manifest(artifact: Artifact, sha: str | None) -> None:
        manifest_entries[artifact.id] = {
            "artifact_id": artifact.id,
            "type": artifact.type,
            "name": artifact.name,
            "version": artifact.version,
            "provenance_label": artifact.provenance_label,
            "sha256": sha,
        }

    figure_count = 0
    for block in blocks:
        if block.type == "heading":
            sections.append({"kind": "heading", "text": block.content.get("text", "")})
        elif block.type == "text":
            sections.append({"kind": "text", "text": block.content.get("text", "")})
        elif block.type == "figure":
            run_id = block.content["run_artifact_id"]
            artifact = db.get(Artifact, run_id)
            run = db.get(Run, run_id)
            if artifact is None or run is None:
                sections.append(
                    {"kind": "unresolved", "text": f"Unresolvable reference: run {run_id}"}
                )
                add_limitation(f"A figure reference ({run_id}) could not be resolved.")
                continue
            figure_count += 1
            array_name = block.content.get("array")
            array_data = None
            array_sha = None
            if array_name and array_name in run.arrays:
                array_sha = run.arrays[array_name]["sha256"]
                array_data = json.loads(objects.get(array_sha))
            add_manifest(artifact, array_sha)
            for binding in run.input_artifacts.values():
                ds_artifact = db.get(Artifact, binding["artifact_id"])
                if ds_artifact is not None:
                    add_manifest(ds_artifact, binding.get("sha256"))
                for unknown in binding.get("unknowns", []):
                    add_limitation(f"Dataset '{ds_artifact.name if ds_artifact else binding['artifact_id']}': {unknown}")
            for warning in run.warnings:
                add_limitation(warning)
            sections.append(
                {
                    "kind": "figure",
                    "number": figure_count,
                    "caption": block.content.get("caption", artifact.name),
                    "run": {
                        "artifact_id": artifact.id,
                        "version": artifact.version,
                        "name": artifact.name,
                        "tool_id": run.tool_id,
                        "tool_version": run.tool_version,
                        "model_name": run.model_name,
                        "method": run.method,
                        "inputs": run.inputs,
                        "outputs": run.outputs,
                        "assumptions": run.assumptions,
                        "guards": run.guards,
                        "checks": run.checks,
                        "environment": run.environment,
                    },
                    "array_json": json.dumps(array_data) if array_data else None,
                    "array_name": array_name,
                }
            )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project.id,
        "notebook": {"artifact_id": notebook.artifact_id, "version": db.get(Artifact, notebook.artifact_id).version},
        "artifacts": sorted(manifest_entries.values(), key=lambda e: e["artifact_id"]),
    }

    html = _env.get_template("report.html").render(
        title=title,
        project=project,
        sections=sections,
        limitations=limitations,
        manifest=manifest,
        manifest_json=json.dumps(manifest, indent=2),
        generated_at=manifest["generated_at"],
    )
    return html, manifest
