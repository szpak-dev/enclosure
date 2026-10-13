import pytest
from django.test import Client


def create_example_diagram_set(client: Client) -> dict[str, object]:
    response = client.post(
        "/api/diagram-sets",
        data={"title": "Example diagrams", "description": "Example diagram contract verification."},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def create_example_diagram(client: Client, diagram_set_id: object) -> dict[str, object]:
    response = client.post(
        f"/api/diagram-sets/{diagram_set_id}/diagrams",
        data={"title": "Example flow", "kind": "flowchart"},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.django_db
def test_rejects_unknown_fields_at_every_diagram_mutation_boundary_without_side_effects() -> None:
    client = Client()
    diagram_set = create_example_diagram_set(client)
    diagram = create_example_diagram(client, diagram_set["id"])

    responses = (
        client.post(
            "/api/diagram-sets",
            data={"title": "Example rejected set", "description": "Example.", "unexpected": True},
            content_type="application/json",
        ),
        client.put(
            f"/api/diagram-sets/{diagram_set['id']}",
            data={"title": "Example replacement", "description": "Example.", "unexpected": True},
            content_type="application/json",
        ),
        client.post(
            f"/api/diagram-sets/{diagram_set['id']}/diagrams",
            data={"title": "Example rejected flow", "kind": "flowchart", "unexpected": True},
            content_type="application/json",
        ),
        client.post(
            f"/api/diagram-sets/{diagram_set['id']}/diagram-batches",
            data={
                "title": "Example rejected batch",
                "kind": "flowchart",
                "commands": [{"operation": "add_start", "arguments": {"id": "start", "label": "Start"}}],
                "unexpected": True,
            },
            content_type="application/json",
        ),
        client.patch(
            f"/api/diagrams/{diagram['id']}",
            data={"expected_revision": diagram["revision"], "title": "Example rejected title", "unexpected": True},
            content_type="application/json",
        ),
        client.post(
            f"/api/diagrams/{diagram['id']}/commands",
            data={
                "expected_revision": diagram["revision"],
                "operation": "add_start",
                "arguments": {"id": "start", "label": "Start"},
                "unexpected": True,
            },
            content_type="application/json",
        ),
        client.post(
            f"/api/diagrams/{diagram['id']}/command-batches",
            data={
                "expected_revision": diagram["revision"],
                "commands": [{"operation": "add_start", "arguments": {"id": "start", "label": "Start"}}],
                "unexpected": True,
            },
            content_type="application/json",
        ),
    )

    assert [response.status_code for response in responses] == [422] * len(responses)
    assert client.get(f"/api/diagram-sets/{diagram_set['id']}").json() == diagram_set
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == diagram
    assert client.get("/api/diagram-sets").json()["items"] == [diagram_set]
    assert client.get(f"/api/diagram-sets/{diagram_set['id']}/diagrams").json()["items"] == [
        {
            "id": diagram["id"],
            "title": diagram["title"],
            "kind": diagram["kind"],
            "revision": diagram["revision"],
        }
    ]


@pytest.mark.django_db
def test_incomplete_diagram_set_replacement_is_rejected_before_complete_replacement_succeeds() -> None:
    client = Client()
    diagram_set = create_example_diagram_set(client)
    url = f"/api/diagram-sets/{diagram_set['id']}"

    incomplete = client.put(
        url,
        data={"title": "Example incomplete replacement"},
        content_type="application/json",
    )

    assert incomplete.status_code == 422
    assert client.get(url).json() == diagram_set

    replaced = client.put(
        url,
        data={"title": "Example replaced diagrams", "description": "Example replacement description."},
        content_type="application/json",
    )

    assert replaced.status_code == 200
    assert replaced.json() == {
        **diagram_set,
        "title": "Example replaced diagrams",
        "description": "Example replacement description.",
        "updated_at": replaced.json()["updated_at"],
    }


@pytest.mark.django_db
def test_blank_titles_are_rejected_before_resource_mutation() -> None:
    client = Client()
    diagram_set = create_example_diagram_set(client)
    diagram = create_example_diagram(client, diagram_set["id"])

    rejected_set = client.post(
        "/api/diagram-sets",
        data={"title": "   ", "description": "Example rejected set."},
        content_type="application/json",
    )
    rejected_diagram = client.patch(
        f"/api/diagrams/{diagram['id']}",
        data={"expected_revision": diagram["revision"], "title": "   "},
        content_type="application/json",
    )

    assert rejected_set.status_code == 422
    assert rejected_diagram.status_code == 422
    assert client.get("/api/diagram-sets").json()["items"] == [diagram_set]
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == diagram
