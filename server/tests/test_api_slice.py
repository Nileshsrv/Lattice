"""API acceptance tests for the vertical slice (A-1/2/4/5-ish/10/11/13 subsets)."""

import pytest

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


def test_stage4_physics_runs_persist_provenance_and_array_artifacts(client, user):
    project_id = create_project(client)
    compton = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "compton.scattering", "inputs": {
            "photon_energy": {"value": 511, "unit": "keV"},
            "angle": {"value": 90, "unit": "deg"},
        }},
    )
    assert compton.status_code == 200, compton.text
    compton_run = compton.json()
    assert compton_run["status"] == "completed"
    assert compton_run["inputs"]["angle"]["unit"] == "rad"
    assert all(check["passed"] for check in compton_run["checks"])
    kn = client.get(f"/api/runs/{compton_run['artifact_id']}/arrays/geometry")
    assert kn.status_code == 200
    assert len(kn.json()["columns"]["angle"]) == 181
    assert "free electron at rest" in str(compton_run["guards"])

    tunneling = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "quantum.rectangular_tunneling", "inputs": {
            "energy": {"value": 0.5, "unit": "eV"},
            "barrier_height": {"value": 1.0, "unit": "eV"},
            "width": {"value": 0.3, "unit": "nm"},
        }},
    )
    assert tunneling.status_code == 200, tunneling.text
    tunnel_run = tunneling.json()
    assert tunnel_run["status"] == "completed"
    assert tunnel_run["inputs"]["mass"]["value"] > 0
    assert all(check["passed"] for check in tunnel_run["checks"])
    assert client.get(f"/api/runs/{tunnel_run['artifact_id']}/arrays/wavefunction").status_code == 200


def test_stage4_analysis_consumes_dataset_reference_and_saves_fit(client, user):
    project_id = create_project(client)
    content = b"x,y\n0,1\n1,3\n2,5\n3,7\n4,9\n"
    dataset = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("line.csv", content, "text/csv")},
        data={"name": "linear observations", "license": "CC0-1.0", "provenance_label": "simulated"},
    ).json()
    fit = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "analysis.linear_regression", "datasets": {"observations": dataset["artifact_id"]}},
    )
    assert fit.status_code == 200, fit.text
    run = fit.json()
    assert run["outputs"]["slope"]["value"] == pytest.approx(2.0)
    assert run["input_artifacts"]["observations"]["sha256"] == dataset["sha256"]
    assert client.get(f"/api/runs/{run['artifact_id']}/arrays/residuals").status_code == 200

    gaussian_csv = b"x,y\n-2,0.1353\n-1,0.6065\n0,1.0000\n1,0.6065\n2,0.1353\n"
    gaussian_dataset = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("peak.csv", gaussian_csv, "text/csv")},
        data={"name": "peak observations", "license": "CC0-1.0", "provenance_label": "simulated"},
    ).json()
    gaussian = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "analysis.gaussian_peak_fit", "datasets": {"observations": gaussian_dataset["artifact_id"]}},
    )
    assert gaussian.status_code == 200, gaussian.text
    gaussian_run = gaussian.json()
    assert gaussian_run["outputs"]["mean"]["value"] == pytest.approx(0.0, abs=1e-3)
    assert gaussian_run["input_artifacts"]["observations"]["sha256"] == gaussian_dataset["sha256"]
    assert client.get(f"/api/runs/{gaussian_run['artifact_id']}/arrays/gaussian_fit").status_code == 200

    propagated = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "analysis.independent_error_propagation", "inputs": {
            "x": {"value": 3}, "sigma_x": {"value": 0.4},
            "y": {"value": 5}, "sigma_y": {"value": 0.2},
        }},
    )
    assert propagated.status_code == 200, propagated.text
    assert propagated.json()["outputs"]["product_sigma"]["value"] > 0


def test_stage4_dataset_window_is_immutable_and_traceable(client, user):
    project_id = create_project(client)
    raw_csv = b"x,y\n0,10\n1,11\n2,12\n3,13\n"
    source = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("observations.csv", raw_csv, "text/csv")},
        data={"name": "raw observations", "license": "CC0-1.0", "provenance_label": "measured"},
    ).json()
    derived_response = client.post(
        f"/api/datasets/{source['artifact_id']}/window",
        json={"column": "x", "minimum": 1, "maximum": 2},
    )
    assert derived_response.status_code == 200, derived_response.text
    derived = derived_response.json()
    assert derived["artifact_id"] != source["artifact_id"]
    assert derived["provenance_label"] == "calculated"
    assert derived["source"]["derived_from"] == source["artifact_id"]
    assert client.get(f"/api/datasets/{derived['artifact_id']}/raw").content == b"x,y\n1,11\n2,12\n"
    assert client.get(f"/api/datasets/{source['artifact_id']}/raw").content == raw_csv
    assert client.get(f"/api/datasets/{derived['artifact_id']}/verify").json()["intact"]


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


def test_stage4_saved_run_comparison(client, user):
    project_id = create_project(client)
    run_a = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "compton.scattering", "inputs": {
            "photon_energy": {"value": 511, "unit": "keV"},
            "angle": {"value": 45, "unit": "deg"},
        }},
    ).json()
    run_b = client.post(
        f"/api/projects/{project_id}/runs",
        json={"tool_id": "compton.scattering", "inputs": {
            "photon_energy": {"value": 511, "unit": "keV"},
            "angle": {"value": 90, "unit": "deg"},
        }},
    ).json()

    # Identical runs cannot be compared
    dup_resp = client.post(
        f"/api/projects/{project_id}/comparisons",
        json={"run_a": run_a["artifact_id"], "run_b": run_a["artifact_id"]},
    )
    assert dup_resp.status_code == 422

    resp = client.post(
        f"/api/projects/{project_id}/comparisons",
        json={"run_a": run_a["artifact_id"], "run_b": run_b["artifact_id"]},
    )
    assert resp.status_code == 200, resp.text
    comp = resp.json()
    assert comp["artifact_id"]
    assert len(comp["runs"]) == 2
    assert comp["parameter_diff"]["angle"]["different"] is True
    assert comp["parameter_diff"]["photon_energy"]["different"] is False
    assert "scattered_energy" in comp["output_diff"]

    detail = client.get(f"/api/comparisons/{comp['artifact_id']}").json()
    assert detail["artifact_id"] == comp["artifact_id"]

    # Activity recorded
    overview = client.get(f"/api/projects/{project_id}").json()
    assert any(ev["kind"] == "runs.compared" for ev in overview["recent_activity"])


def test_stage4_public_archive_spectrum_ingest_and_analysis(client, user):
    from pathlib import Path
    project_id = create_project(client)
    csv_path = Path(__file__).resolve().parents[2] / "sample_data" / "calspec-sun-stis.csv"
    assert csv_path.exists(), f"Missing archive spectrum file: {csv_path}"
    content = csv_path.read_bytes()

    dataset = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("calspec-sun-stis.csv", content, "text/csv")},
        data={
            "name": "HST CALSPEC Sun Reference Spectrum",
            "license": "CC0-1.0",
            "provenance_label": "measured",
        },
    ).json()
    assert dataset["provenance_label"] == "measured"
    assert dataset["unknowns"] == []
    cols = {c["name"]: c["unit"] for c in dataset["columns"]}
    assert cols["wavelength"] == "nm"
    assert cols["flux"] == "erg/(s*cm2*Angstrom)"

    # Run blackbody fit on the real observed solar spectrum (optical range 350-850 nm)
    fit_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "stellar.blackbody_fit",
            "inputs": {
                "lambda_min": {"value": 350.0, "unit": "nm"},
                "lambda_max": {"value": 850.0, "unit": "nm"},
            },
            "datasets": {"spectrum": dataset["artifact_id"]},
        },
    )
    assert fit_resp.status_code == 200, fit_resp.text
    run = fit_resp.json()
    assert run["status"] == "completed"
    t_eff = run["outputs"]["T_eff"]["value"]
    # Solar optical continuum effective temperature ~5588 K (blanketed optical spectrum)
    assert 5400.0 < t_eff < 5800.0
    assert all(c["passed"] for c in run["checks"])
    assert run["input_artifacts"]["spectrum"]["sha256"] == dataset["sha256"]



def test_a9_anchored_comments(client, user):
    """A-9: Anchored comments on artifacts (create, list, resolve, soft-delete semantics)."""
    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv())

    artifact_id = ds["artifact_id"]
    anchor = {"type": "field", "field": "name"}

    # POST comment anchored to the dataset artifact
    resp = client.post(
        f"/api/artifacts/{artifact_id}/comments",
        json={"text": "This field looks wrong", "anchor": anchor},
    )
    assert resp.status_code == 200, resp.text
    comment = resp.json()
    assert comment["text"] == "This field looks wrong"
    assert comment["anchor"] == anchor
    assert comment["artifact_id"] == artifact_id
    assert comment["project_id"] == project_id
    assert comment["resolved"] is False
    assert comment["resolved_at"] is None
    comment_id = comment["id"]

    # GET comments on artifact — verify comment present
    resp = client.get(f"/api/artifacts/{artifact_id}/comments")
    assert resp.status_code == 200, resp.text
    comments = resp.json()
    ids = [c["id"] for c in comments]
    assert comment_id in ids

    # GET project-wide comments — same comment appears
    resp = client.get(f"/api/projects/{project_id}/comments")
    assert resp.status_code == 200, resp.text
    proj_comments = resp.json()
    ids = [c["id"] for c in proj_comments]
    assert comment_id in ids

    # PATCH to resolve the comment
    resp = client.patch(f"/api/comments/{comment_id}", json={"resolved": True})
    assert resp.status_code == 200, resp.text
    patched = resp.json()
    assert patched["resolved"] is True
    assert patched["resolved_at"] is not None

    # Resolved comment still present when include_resolved=true (soft-delete semantics)
    resp = client.get(f"/api/artifacts/{artifact_id}/comments?include_resolved=true")
    assert resp.status_code == 200, resp.text
    all_comments = resp.json()
    ids = [c["id"] for c in all_comments]
    assert comment_id in ids

    # Resolved comment hidden from default listing (resolved=False filter)
    resp = client.get(f"/api/artifacts/{artifact_id}/comments")
    assert resp.status_code == 200, resp.text
    active_comments = resp.json()
    ids = [c["id"] for c in active_comments]
    assert comment_id not in ids


# ---------------------------------------------------------------------------
# A-12: Review state transitions
# ---------------------------------------------------------------------------

def test_a12_review_state_transitions(client, user):
    from tests.conftest import create_project, synthetic_spectrum_csv, upload_spectrum

    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv())

    # Create a run to have an artifact with review_state
    run_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "stellar.blackbody_fit",
            "inputs": {},
            "datasets": {"spectrum": ds["artifact_id"]},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    run = run_resp.json()
    artifact_id = run["artifact_id"]

    # Any member can set "needs-review"
    resp = client.patch(
        f"/api/artifacts/{artifact_id}/review",
        json={"state": "needs-review"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["new_state"] == "needs-review"
    assert data["artifact_id"] == artifact_id
    # Must NOT contain "platform-validated"
    assert "platform-validated" not in resp.text

    # Owner can approve
    resp = client.patch(
        f"/api/artifacts/{artifact_id}/review",
        json={"state": "approved"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["new_state"] == "approved"
    assert "platform-validated" not in resp.text

    # ActivityEvent recorded with correct kind
    overview = client.get(f"/api/projects/{project_id}").json()
    kinds = [e["kind"] for e in overview["recent_activity"]]
    assert "review_state_changed" in kinds

    # Non-member / viewer cannot approve
    from tests.conftest import make_client_with_user
    other_client, other_user = make_client_with_user()
    # Add as viewer (cannot approve)
    client.post(
        f"/api/projects/{project_id}/members",
        json={"username": other_user["username"], "role": "viewer"},
    )
    resp2 = other_client.patch(
        f"/api/artifacts/{artifact_id}/review",
        json={"state": "archived"},
    )
    assert resp2.status_code == 403


# ---------------------------------------------------------------------------
# A-6: Variant branching / lineage
# ---------------------------------------------------------------------------

def test_a6_variants_maintain_lineage(client, user):
    from tests.conftest import create_project, synthetic_spectrum_csv, upload_spectrum

    project_id = create_project(client)
    ds = upload_spectrum(client, project_id, synthetic_spectrum_csv())

    def make_run(parent_run=None):
        body = {
            "tool_id": "stellar.blackbody_fit",
            "inputs": {},
            "datasets": {"spectrum": ds["artifact_id"]},
        }
        if parent_run is not None:
            body["parent_run"] = parent_run
        resp = client.post(f"/api/projects/{project_id}/runs", json=body)
        assert resp.status_code == 200, resp.text
        return resp.json()

    baseline = make_run()
    baseline_id = baseline["artifact_id"]
    assert baseline["parent_run"] is None

    variant1 = make_run(parent_run=baseline_id)
    variant1_id = variant1["artifact_id"]
    assert variant1["parent_run"] == baseline_id

    variant2 = make_run(parent_run=baseline_id)
    variant2_id = variant2["artifact_id"]
    assert variant2["parent_run"] == baseline_id

    # GET lineage of variant1 — baseline must appear
    lineage_resp = client.get(f"/api/runs/{variant1_id}/lineage")
    assert lineage_resp.status_code == 200, lineage_resp.text
    chain = lineage_resp.json()

    ids_in_chain = [entry["artifact_id"] for entry in chain]
    assert variant1_id in ids_in_chain
    assert baseline_id in ids_in_chain

    # Baseline is the root — its parent_run should be None
    baseline_entry = next(e for e in chain if e["artifact_id"] == baseline_id)
    assert baseline_entry["parent_run"] is None

    # Verify all three runs exist
    for rid in (baseline_id, variant1_id, variant2_id):
        r = client.get(f"/api/runs/{rid}")
        assert r.status_code == 200

    # Invalid parent_run is rejected
    bad_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "stellar.blackbody_fit",
            "inputs": {},
            "datasets": {"spectrum": ds["artifact_id"]},
            "parent_run": "nonexistent-id-00000000",
        },
    )
    assert bad_resp.status_code == 422


# ---------------------------------------------------------------------------
# Stage 5: AI Assistant, Chained Analysis (A-8), Report Staleness & Type
# ---------------------------------------------------------------------------

def test_stage5_ai_assistant_does_not_invent_numbers(client, user):
    project_id = create_project(client)

    # Query assistant
    resp = client.post(
        f"/api/projects/{project_id}/assistant",
        json={"message": "Can you help me compute Compton scattering for 511 keV photons?"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["provenance_label"] == "ai-suggested"
    assert data["tool_plan"] is not None
    assert data["tool_plan"]["tool_name"] == "compton.scattering"
    assert data["tool_plan"]["requires_user_approval"] is True
    # Ensure text suggests rather than asserts calculated values
    assert "No physics values will be computed until you approve" in data["text"]

    # Cancelled execution
    cancel_resp = client.post(
        f"/api/projects/{project_id}/assistant/execute",
        json={"tool_plan": data["tool_plan"], "approved": False},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Approved execution with valid inputs
    plan = {
        "tool_name": "compton.scattering",
        "params": {
            "photon_energy": {"value": 511.0, "unit": "keV"},
            "angle": {"value": 90.0, "unit": "deg"},
        },
    }
    exec_resp = client.post(
        f"/api/projects/{project_id}/assistant/execute",
        json={"tool_plan": plan, "approved": True},
    )
    assert exec_resp.status_code == 200, exec_resp.text
    exec_data = exec_resp.json()
    assert exec_data["status"] == "executed"
    run_id = exec_data["run_id"]

    # Verify run exists and has provenance_label "ai-suggested"
    run_detail = client.get(f"/api/runs/{run_id}").json()
    assert run_detail["provenance_label"] == "ai-suggested"
    assert run_detail["status"] == "completed"
    assert "scattered_energy" in run_detail["outputs"]


def test_a8_chained_analysis_no_reupload(client, user):
    project_id = create_project(client)

    # 1. Run quantum tunneling energy sweep
    sweep_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "quantum.rectangular_tunneling_sweep",
            "inputs": {
                "energy_min": {"value": 0.1, "unit": "eV"},
                "energy_max": {"value": 0.9, "unit": "eV"},
                "barrier_height": {"value": 1.0, "unit": "eV"},
                "width": {"value": 0.2, "unit": "nm"},
                "points": {"value": 51},
            },
        },
    )
    assert sweep_resp.status_code == 200, sweep_resp.text
    sweep_run = sweep_resp.json()
    assert sweep_run["status"] == "completed"
    assert "energy_sweep" in sweep_run["arrays"]

    # 2. Promote the sweep array directly to a dataset artifact (mapping energy->x, transmission->y)
    promote_resp = client.post(
        f"/api/runs/{sweep_run['artifact_id']}/arrays/energy_sweep/promote",
        json={
            "name": "Promoted Tunnelling Sweep",
            "column_mapping": {"energy": "x", "transmission": "y"},
        },
    )
    assert promote_resp.status_code == 200, promote_resp.text
    promoted_ds = promote_resp.json()
    assert promoted_ds["artifact_id"]
    col_names = [c["name"] for c in promoted_ds["columns"]]
    assert "x" in col_names and "y" in col_names

    # 3. Chain into linear regression without re-uploading
    fit_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "tool_id": "analysis.linear_regression",
            "datasets": {"observations": promoted_ds["artifact_id"]},
        },
    )
    assert fit_resp.status_code == 200, fit_resp.text
    fit_run = fit_resp.json()
    assert fit_run["status"] == "completed"
    assert fit_run["input_artifacts"]["observations"]["artifact_id"] == promoted_ds["artifact_id"]
    assert "slope" in fit_run["outputs"]


def test_stage5_report_staleness_and_type(client, user):
    project_id = create_project(client)

    # Create notebook and add a block
    nb_resp = client.post(
        f"/api/projects/{project_id}/notebooks",
        json={"title": "Analysis Notebook"},
    )
    assert nb_resp.status_code == 200
    nb_id = nb_resp.json()["artifact_id"]

    # Create report with report_type
    rep_resp = client.post(
        f"/api/projects/{project_id}/reports",
        json={
            "title": "Comprehensive Stellar Report",
            "notebook_id": nb_id,
            "report_type": "lab-report",
        },
    )
    assert rep_resp.status_code == 200, rep_resp.text
    rep_id = rep_resp.json()["artifact_id"]
    assert rep_resp.json()["report_type"] == "lab-report"

    # Export report version
    exp_resp = client.post(f"/api/reports/{rep_id}/export")
    assert exp_resp.status_code == 200

    # Staleness check right after export: fresh (not stale)
    stale_resp = client.get(f"/api/reports/{rep_id}/staleness")
    assert stale_resp.status_code == 200
    assert stale_resp.json()["stale"] is False
