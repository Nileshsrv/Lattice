"""API acceptance tests for the vertical slice (A-1/2/4/5-ish/10/11/13 subsets)."""

from tests.conftest import (
    create_project,
    make_client_with_user,
    synthetic_spectrum_csv,
    upload_spectrum,
)


def test_a1_private_by_default_and_roles(client, user):
    project_id = create_project(client)
    other_client, other_user = make_client_with_user()
    # Non-member sees 404, not 403: existence is not leaked.
    assert other_client.get(f"/api/projects/{project_id}").status_code == 404
    # Viewer can see but not upload.
    resp = client.post(
        f"/api/projects/{project_id}/members",
        json={"username": other_user["username"], "role": "viewer"},
    )
    assert resp.status_code == 200
    assert other_client.get(f"/api/projects/{project_id}").status_code == 200
    resp = other_client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("x.csv", b"wavelength_nm,flux\n500,1\n", "text/csv")},
        data={"name": "x"},
    )
    assert resp.status_code == 403
    # Membership landed in the audit trail.
    overview = client.get(f"/api/projects/{project_id}").json()
    kinds = [e["kind"] for e in overview["recent_activity"]]
    assert "member.added" in kinds and "project.created" in kinds


def test_a2_a3_dataset_ingest_hash_unknowns(client, user):
    project_id = create_project(client)
    csv = synthetic_spectrum_csv()
    ds = upload_spectrum(client, project_id, csv, license_str="")
    # Column units parsed from headers; undeclared flux unit + missing license flagged.
    cols = {c["name"]: c["unit"] for c in ds["columns"]}
    assert cols["wavelength"] == "nm"
    assert cols["flux"] is None
    assert any("flux" in u for u in ds["unknowns"])
    assert any("license" in u for u in ds["unknowns"])
    # Raw bytes round-trip exactly; stored hash verifies (I-1).
    raw = client.get(f"/api/datasets/{ds['artifact_id']}/raw").content
    assert raw == csv
    verify = client.get(f"/api/datasets/{ds['artifact_id']}/verify").json()
    assert verify["intact"] and verify["stored_sha256"] == ds["sha256"]


def test_a4_a5_run_provenance_and_immutability(client, user):
    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv(t_eff=6000.0))

    def run_fit(window=None):
        inputs = {}
        if window:
            inputs = {
                "lambda_min": {"value": window[0], "unit": "nm"},
                "lambda_max": {"value": window[1], "unit": "nm"},
            }
        resp = client.post(
            f"/api/projects/{project_id}/runs",
            json={
                "tool_id": "stellar.blackbody_fit",
                "inputs": inputs,
                "datasets": {"spectrum": ds["artifact_id"]},
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    run1 = run_fit()
    # Full provenance record (c-schemas §3).
    assert run1["status"] == "completed"
    assert run1["tool_version"] == "0.1.0"
    assert run1["model_name"]
    assert run1["method"]["name"].startswith("nonlinear least squares")
    assert run1["input_artifacts"]["spectrum"]["sha256"] == ds["sha256"]
    assert run1["environment"]["numpy"] and run1["environment"]["scipy"]
    assert "CODATA" in run1["environment"]["constants_source"]
    assert run1["environment"]["execution_location"] == "local"
    assert run1["assumptions"] and run1["checks"]
    assert all(c["passed"] for c in run1["checks"])
    # A-13: guards rendered with the result payload.
    assert any("composition" in g for g in run1["guards"])
    t1 = run1["outputs"]["T_eff"]["value"]
    assert run1["outputs"]["T_eff"]["unit"] == "K"
    assert run1["outputs"]["T_eff"]["sigma"] is not None

    # Determinism: identical inputs reproduce identical outputs.
    run2 = run_fit()
    assert run2["artifact_id"] != run1["artifact_id"]
    assert run2["outputs"]["T_eff"]["value"] == t1

    # Changing a parameter creates a NEW run; the old run is untouched (I-6).
    run3 = run_fit(window=(400.0, 900.0))
    assert run3["artifact_id"] not in (run1["artifact_id"], run2["artifact_id"])
    run1_again = client.get(f"/api/runs/{run1['artifact_id']}").json()
    assert run1_again["outputs"] == run1["outputs"]
    assert run1_again["inputs"] == run1["inputs"]

    # Inputs were converted to canonical SI units and recorded with units (I-9).
    assert run3["inputs"]["lambda_min"]["unit"] == "m"
    assert abs(run3["inputs"]["lambda_min"]["value"] - 4.0e-7) < 1e-18

    # Stored arrays are retrievable data, not screenshots (R9).
    arrays = client.get(f"/api/runs/{run1['artifact_id']}/arrays/fit").json()
    assert set(arrays["columns"]) == {"wavelength", "flux", "fitted", "residual"}
    assert len(arrays["columns"]["wavelength"]) == len(arrays["columns"]["fitted"])


def test_a4_validation_rejects_not_clamps(client, user):
    project_id = create_project(client)
    resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "stellar.wien_temperature",
            "inputs": {"lambda_max": {"value": 502, "unit": "kg"}},
        },
    )
    assert resp.status_code == 422
    assert "not convertible" in str(resp.json()["detail"]["input_errors"])


def test_a10_notebook_blocks_and_conflict(client, user):
    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv())
    run = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "stellar.blackbody_fit", "datasets": {"spectrum": ds["artifact_id"]}},
    ).json()
    nb = client.post(
        f"/api/projects/{project_id}/notebooks", json={"title": "Analysis"}
    ).json()
    nb_id = nb["artifact_id"]
    client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={"type": "heading", "content": {"text": "Results"}},
    )
    block = client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={"type": "text", "content": {"text": "The fitted temperature is shown below."}},
    ).json()
    fig = client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={
            "type": "figure",
            "content": {
                "run_artifact_id": run["artifact_id"],
                "array": "fit",
                "caption": "Blackbody fit to the test spectrum",
            },
        },
    ).json()
    # Figure blocks store a reference bound to the run version, not values.
    detail = client.get(f"/api/notebooks/{nb_id}").json()
    fig_block = next(b for b in detail["blocks"] if b["type"] == "figure")
    assert fig_block["content"]["run_version"] == 1
    assert "T_eff" not in str(fig_block["content"])

    # Editing prose never touches the run (I-6 via A-10).
    resp = client.patch(
        f"/api/blocks/{block['id']}",
        json={"content": {"text": "Edited prose."}, "revision": block["revision"]},
    )
    assert resp.status_code == 200
    run_after = client.get(f"/api/runs/{run['artifact_id']}").json()
    assert run_after["outputs"] == run["outputs"]

    # Stale revision is rejected with the server copy returned (I-8), applied nowhere.
    resp = client.patch(
        f"/api/blocks/{block['id']}",
        json={"content": {"text": "Conflicting edit."}, "revision": block["revision"]},
    )
    assert resp.status_code == 409
    body = resp.json()["detail"]
    assert body["server_content"]["text"] == "Edited prose."
    # A figure block cannot reference a run from outside the project.
    other_client, other_user = make_client_with_user()
    other_project = create_project(other_client, name="Other")
    other_ds = upload_spectrum(other_client, other_project, synthetic_spectrum_csv())
    foreign_run = other_client.post(
        f"/api/projects/{other_project}/runs",
        json={"tool_id": "stellar.blackbody_fit", "datasets": {"spectrum": other_ds["artifact_id"]}},
    ).json()
    resp = client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={"type": "figure", "content": {"run_artifact_id": foreign_run["artifact_id"]}},
    )
    assert resp.status_code == 422


def test_a11_report_generation_manifest_and_freezing(client, user):
    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv(), license_str="")
    run = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "stellar.blackbody_fit", "datasets": {"spectrum": ds["artifact_id"]}},
    ).json()
    nb = client.post(f"/api/projects/{project_id}/notebooks", json={"title": "NB"}).json()
    nb_id = nb["artifact_id"]
    client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={"type": "heading", "content": {"text": "Results"}},
    )
    client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={
            "type": "figure",
            "content": {"run_artifact_id": run["artifact_id"], "array": "fit",
                        "caption": "Fit"},
        },
    )
    report = client.post(
        f"/api/projects/{project_id}/reports",
        json={"title": "Slice report", "notebook_id": nb_id},
    ).json()
    export1 = client.post(f"/api/reports/{report['artifact_id']}/export").json()
    assert export1["version"] == 1
    manifest_ids = {e["artifact_id"] for e in export1["manifest"]["artifacts"]}
    # The run AND its input dataset are frozen into the manifest (I-10).
    assert run["artifact_id"] in manifest_ids
    assert ds["artifact_id"] in manifest_ids
    ds_entry = next(
        e for e in export1["manifest"]["artifacts"] if e["artifact_id"] == ds["artifact_id"]
    )
    assert ds_entry["sha256"] == ds["sha256"]
    assert ds_entry["provenance_label"] == "simulated"

    html = client.get(
        f"/api/reports/{report['artifact_id']}/versions/1/html"
    ).text
    assert "Figure 1." in html
    assert "does not determine elemental composition" in html
    # Limitations carry the dataset unknowns and run warnings (I-11).
    assert "license/attribution not provided" in html
    assert "statistical only" in html

    # Re-export is a NEW version; version 1 stays byte-identical.
    client.post(
        f"/api/notebooks/{nb_id}/blocks",
        json={"type": "text", "content": {"text": "Added after first export."}},
    )
    export2 = client.post(f"/api/reports/{report['artifact_id']}/export").json()
    assert export2["version"] == 2
    html1_again = client.get(
        f"/api/reports/{report['artifact_id']}/versions/1/html"
    ).text
    assert html1_again == html
    html2 = client.get(f"/api/reports/{report['artifact_id']}/versions/2/html").text
    assert "Added after first export." in html2 and "Added after first export." not in html


def test_wien_tool_end_to_end(client, user):
    project_id = create_project(client)
    resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "stellar.wien_temperature",
            "inputs": {"lambda_max": {"value": 502.0, "unit": "nm"}},
        },
    )
    assert resp.status_code == 200, resp.text
    run = resp.json()
    t = run["outputs"]["T_eff"]["value"]
    assert 5700 < t < 5820
    assert run["inputs"]["lambda_max"]["unit"] == "m"
