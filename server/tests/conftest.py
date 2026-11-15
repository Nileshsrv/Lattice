import io
import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient

from lattice.app import app
from lattice.physics.planck import planck_lambda, wien_lambda_max


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def user(client):
    name = f"user_{uuid.uuid4().hex[:10]}"
    resp = client.post(
        "/api/auth/register", json={"username": name, "password": "correct-horse-9"}
    )
    assert resp.status_code == 200, resp.text
    return {"username": name, **resp.json()}


def make_client_with_user():
    c = TestClient(app)
    name = f"user_{uuid.uuid4().hex[:10]}"
    resp = c.post("/api/auth/register", json={"username": name, "password": "correct-horse-9"})
    assert resp.status_code == 200, resp.text
    return c, {"username": name, **resp.json()}


def synthetic_spectrum_csv(
    t_eff: float = 6000.0, noise: float = 0.01, seed: int = 7
) -> bytes:
    rng = np.random.default_rng(seed)
    wl_nm = np.arange(320.0, 1000.0, 0.5)
    wl_m = wl_nm * 1e-9
    peak = wien_lambda_max(t_eff)
    flux = planck_lambda(wl_m, t_eff) / planck_lambda(peak, t_eff)
    flux = flux + rng.normal(0.0, noise, wl_nm.size)
    buf = io.StringIO()
    buf.write("wavelength_nm,flux\n")
    for w, f in zip(wl_nm, flux):
        buf.write(f"{w:.1f},{f:.6f}\n")
    return buf.getvalue().encode()


def create_project(client, name="Test project") -> str:
    resp = client.post(
        "/api/projects",
        json={"name": name, "research_question": "What is T_eff of the test star?"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def upload_spectrum(client, project_id, content: bytes, license_str="CC0-1.0") -> dict:
    resp = client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": ("spectrum.csv", content, "text/csv")},
        data={
            "name": "test spectrum",
            "license": license_str,
            "provenance_label": "simulated",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
