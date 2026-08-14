import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.mark.django_db
def test_siren_projects_stale_diagram_revision_as_domain_error() -> None:
    client = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)
    diagram_set = client.post(
        "/siren/diagram-sets",
        data={"title": "Concurrency", "description": "Siren error projection."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201

    diagram = client.post(
        f"/siren/diagram-sets/{diagram_set.json()['properties']['id']}/diagrams",
        data={"title": "Flow", "kind": "flowchart"},
        content_type="application/json",
    )
    assert diagram.status_code == 201
    diagram_id = diagram.json()["properties"]["id"]

    applied = client.post(
        f"/siren/diagrams/{diagram_id}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_start",
            "arguments": {"id": "start", "label": "Start"},
        },
        content_type="application/json",
    )
    assert applied.status_code == 200
    assert applied.json()["properties"]["revision"] == 2

    response = client.post(
        f"/siren/diagrams/{diagram_id}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_end",
            "arguments": {"id": "end", "label": "End"},
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {
        "detail": f"Diagram {diagram_id!r} revision conflict: expected 1, current revision is 2.",
        "status": 422,
    }
