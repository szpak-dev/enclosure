import pytest
from django.test import Client


def create_diagram(client: Client, kind: str = "flowchart") -> dict[str, object]:
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Error handling", "description": "Diagram API error tests."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201

    diagram = client.post(
        f"/api/diagram-sets/{diagram_set.json()['id']}/diagrams",
        data={"title": "Test diagram", "kind": kind},
        content_type="application/json",
    )
    assert diagram.status_code == 201
    return diagram.json()


@pytest.mark.django_db
def test_unknown_kind_returns_domain_error() -> None:
    response = Client().get("/api/diagrams/kinds/missing")

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.django_db
def test_unknown_command_returns_domain_error() -> None:
    client = Client()
    diagram = create_diagram(client)

    response = client.post(
        f"/api/diagrams/{diagram['id']}/commands",
        data={"expected_revision": 1, "operation": "missing", "arguments": {}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.django_db
def test_invalid_command_arguments_return_domain_error() -> None:
    client = Client()
    diagram = create_diagram(client)

    response = client.post(
        f"/api/diagrams/{diagram['id']}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_start",
            "arguments": {"id": "start"},
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.django_db
def test_stale_revision_returns_domain_error() -> None:
    client = Client()
    diagram = create_diagram(client)
    diagram_url = f"/api/diagrams/{diagram['id']}"

    applied = client.post(
        f"{diagram_url}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_start",
            "arguments": {"id": "start", "label": "Start"},
        },
        content_type="application/json",
    )
    assert applied.status_code == 200
    assert applied.json()["revision"] == 2

    response = client.post(
        f"{diagram_url}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_end",
            "arguments": {"id": "end", "label": "End"},
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            f"Diagram {diagram['id']!r} revision conflict: expected 1, current revision is 2."
        )
    }
