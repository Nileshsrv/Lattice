"""Polish pass tests: equation blocks, memory watchdog, PDF export."""

import os

import pytest

from lattice.runs.orchestrator import rss_over_limit
from tests.conftest import create_project


def _notebook_with_equation(client, project_id):
    nb = client.post(
        f"/api/projects/{project_id}/notebooks", json={"title": "NB"}
    ).json()
    resp = client.post(
        f"/api/notebooks/{nb['artifact_id']}/blocks",
        json={"type": "equation", "content": {"latex": r"\lambda_{max} T = b"}},
    )
    assert resp.status_code == 200, resp.text
    return nb


def test_equation_block_roundtrip_and_report(client, user):
    project_id = create_project(client)
    nb = _notebook_with_equation(client, project_id)
    detail = client.get(f"/api/notebooks/{nb['artifact_id']}").json()
    eq = next(b for b in detail["blocks"] if b["type"] == "equation")
    assert eq["content"]["latex"] == r"\lambda_{max} T = b"

    report = client.post(
        f"/api/projects/{project_id}/reports",
        json={"title": "Equations", "notebook_id": nb["artifact_id"]},
    ).json()
    export = client.post(f"/api/reports/{report['artifact_id']}/export").json()
    html = client.get(
        f"/api/reports/{report['artifact_id']}/versions/{export['version']}/html"
    ).text
    # Equation rendered as a numbered display block with its LaTeX carried along.
    assert "data-latex=" in html and "(1)" in html
    assert "katex" in html.lower()


def test_unknown_block_type_still_rejected(client, user):
    project_id = create_project(client)
    nb = client.post(
        f"/api/projects/{project_id}/notebooks", json={"title": "NB"}
    ).json()
    resp = client.post(
        f"/api/notebooks/{nb['artifact_id']}/blocks",
        json={"type": "video", "content": {}},
    )
    assert resp.status_code == 422


def test_memory_watchdog_detects_over_limit_process():
    pid = os.getpid()
    # This process certainly uses more than 1 byte...
    assert rss_over_limit([pid], 1) is not None
    # ...and certainly less than 1 TB.
    assert rss_over_limit([pid], 1024**4) is None
    # Dead/unknown pids are skipped, not fatal.
    assert rss_over_limit([99999999], 1) is None


def test_pdf_export(client, user):
    pytest.importorskip("playwright.sync_api")
    project_id = create_project(client)
    nb = _notebook_with_equation(client, project_id)
    report = client.post(
        f"/api/projects/{project_id}/reports",
        json={"title": "PDF test", "notebook_id": nb["artifact_id"]},
    ).json()
    export = client.post(f"/api/reports/{report['artifact_id']}/export").json()
    resp = client.get(
        f"/api/reports/{report['artifact_id']}/versions/{export['version']}/pdf"
    )
    if resp.status_code == 503:
        pytest.skip(f"PDF renderer unavailable: {resp.json()['detail']}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    # Second fetch serves the cached object, byte-identical.
    again = client.get(
        f"/api/reports/{report['artifact_id']}/versions/{export['version']}/pdf"
    )
    assert again.content == resp.content
