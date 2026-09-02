from urllib.parse import urlsplit

import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.mark.django_db
def test_siren_diagram_set_advertises_its_diagram_collection() -> None:
    client = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)
    diagram_set = client.post(
        "/siren/diagram-sets",
        data={"title": "Architecture", "description": "Related diagrams."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201
    created_document = diagram_set.json()
    diagram_set_id = created_document["properties"]["id"]
    created_collection_link = next(link for link in created_document["links"] if "collection" in link["rel"])
    assert urlsplit(created_collection_link["href"]).path == (f"/siren/diagram-sets/{diagram_set_id}/diagrams")

    diagram = client.post(
        f"/siren/diagram-sets/{diagram_set_id}/diagrams",
        data={"title": "System context", "kind": "flowchart"},
        content_type="application/json",
    )
    assert diagram.status_code == 201

    response = client.get(f"/siren/diagram-sets/{diagram_set_id}")

    assert response.status_code == 200
    document = response.json()
    assert "diagrams" not in document["properties"]
    collection_link = next(link for link in document["links"] if "collection" in link["rel"])
    assert collection_link["rel"] == ["collection"]
    assert urlsplit(collection_link["href"]).path == f"/siren/diagram-sets/{diagram_set_id}/diagrams"

    collection = client.get(urlsplit(collection_link["href"]).path)

    assert collection.status_code == 200
    collection_document = collection.json()
    assert collection_document["class"] == ["collection", "diagram"]
    assert len(collection_document["entities"]) == 1
    item = collection_document["entities"][0]
    assert item["rel"] == ["item"]
    self_link = next(link for link in item["links"] if "self" in link["rel"])
    assert urlsplit(self_link["href"]).path == (
        f"/siren/diagram-sets/{diagram_set_id}/diagrams/{diagram.json()['properties']['id']}"
    )

    global_collection = client.get("/siren/diagrams")

    assert global_collection.status_code == 200
    assert global_collection.json()["entities"][0]["properties"] == item["properties"]

    updated = client.patch(
        f"/siren/diagram-sets/{diagram_set_id}",
        data={"title": "Updated architecture"},
        content_type="application/json",
    )

    assert updated.status_code == 200
    updated_collection_link = next(link for link in updated.json()["links"] if "collection" in link["rel"])
    assert updated_collection_link["href"] == collection_link["href"]


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
