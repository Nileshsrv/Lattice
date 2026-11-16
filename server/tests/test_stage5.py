"""Stage 5 acceptance tests: assistant, presence, anchored notebook comments."""

import pytest

from tests.conftest import create_project, make_client_with_user


def test_assistant_suggests_registered_tools_only(client, user):
    project_id = create_project(client)
    # Stellar keywords must map to a REAL registry id (regression: 'stellar.wien'
    # did not exist, so stellar suggestions silently never fired).
    reply = client.post(
        f"/api/projects/{project_id}/assistant",
        json={"message": "fit a blackbody to my spectrum"},
    ).json()
    assert reply["provenance_label"] == "ai-suggested"
    assert reply["tool_plan"]["tool_name"] == "stellar.blackbody_fit"
    assert reply["tool_plan"]["needs_dataset"] is True
    assert any("composition" in g for g in reply["tool_plan"]["guards"])

    reply = client.post(
        f"/api/projects/{project_id}/assistant",
        json={"message": "compute compton scattering at 90 degrees"},
    ).json()
    assert reply["tool_plan"]["tool_name"] == "compton.scattering"

    reply = client.post(
        f"/api/projects/{project_id}/assistant",
        json={"message": "estimate temperature from the wien displacement peak"},
    ).json()
    assert reply["tool_plan"]["tool_name"] == "stellar.wien_temperature"

    # No keyword match → no plan, and the text asserts no values.
    reply = client.post(
        f"/api/projects/{project_id}/assistant", json={"message": "hello there"}
    ).json()
    assert reply["tool_plan"] is None


def test_assistant_execution_is_approval_gated_and_provenance_labelled(client, user):
    project_id = create_project(client)
    plan = {
        "tool_name": "stellar.wien_temperature",
        "params": {"lambda_max": {"value": 502.0, "unit": "nm"}},
    }
    # Not approved → nothing executes.
    response = client.post(
        f"/api/projects/{project_id}/assistant/execute",
        json={"tool_plan": plan, "approved": False},
    ).json()
    assert response["status"] == "cancelled"
    assert client.get(f"/api/projects/{project_id}/runs").json() == []

    # Approved → a real run with ai-suggested provenance, numbers from the tool.
    response = client.post(
        f"/api/projects/{project_id}/assistant/execute",
        json={"tool_plan": plan, "approved": True},
    ).json()
    assert response["status"] == "executed"
    run = client.get(f"/api/runs/{response['run_id']}").json()
    assert run["status"] == "completed"
    assert run["provenance_label"] == "ai-suggested"
    assert 5700 < run["outputs"]["T_eff"]["value"] < 5820
    assert "CODATA" in run["environment"]["constants_source"]


def test_assistant_refuses_dataset_tools(client, user):
    project_id = create_project(client)
    response = client.post(
        f"/api/projects/{project_id}/assistant/execute",
        json={"tool_plan": {"tool_name": "stellar.blackbody_fit", "params": {}}, "approved": True},
    )
    assert response.status_code == 422
    assert "dataset" in response.json()["detail"]


def test_presence_websocket(client, user):
    project_id = create_project(client)
    with client.websocket_connect(f"/api/ws/projects/{project_id}") as ws:
        message = ws.receive_json()
        assert message["type"] == "presence"
        assert user["username"] in message["users"]

        # A second member joining is broadcast to the first socket.
        other_client, other_user = make_client_with_user()
        client.post(
            f"/api/projects/{project_id}/members",
            json={"username": other_user["username"], "role": "collaborator"},
        )
        with other_client.websocket_connect(f"/api/ws/projects/{project_id}") as ws2:
            joined = ws.receive_json()
            assert set(joined["users"]) == {user["username"], other_user["username"]}
            assert ws2.receive_json()["users"] == joined["users"]
        left = ws.receive_json()
        assert left["users"] == [user["username"]]


def test_presence_rejects_non_members(client, user):
    project_id = create_project(client)
    outsider, _outsider_user = make_client_with_user()
    with pytest.raises(Exception):
        with outsider.websocket_connect(f"/api/ws/projects/{project_id}") as ws:
            ws.receive_json()


def test_notebook_comments_anchor_to_blocks(client, user):
    project_id = create_project(client)
    nb = client.post(
        f"/api/projects/{project_id}/notebooks", json={"title": "NB"}
    ).json()
    block = client.post(
        f"/api/notebooks/{nb['artifact_id']}/blocks",
        json={"type": "text", "content": {"text": "A paragraph."}},
    ).json()
    comment = client.post(
        f"/api/artifacts/{nb['artifact_id']}/comments",
        json={"text": "Is this claim supported?", "anchor": {"block_id": block["id"]}},
    ).json()
    assert comment["anchor"] == {"block_id": block["id"]}
    assert comment["artifact_version"] >= 1

    comments = client.get(f"/api/artifacts/{nb['artifact_id']}/comments").json()
    assert len(comments) == 1
    resolved = client.patch(
        f"/api/comments/{comment['id']}", json={"resolved": True}
    ).json()
    assert resolved["resolved"] and resolved["resolved_by"]
    assert client.get(f"/api/artifacts/{nb['artifact_id']}/comments").json() == []
