import pytest
from django.test import Client


def create_diagram_set(client: Client, title: str) -> dict[str, object]:
    response = client.post(
        "/api/diagram-sets",
        data={"title": title, "description": f"Diagrams for {title}."},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def create_diagram(client: Client, diagram_set_id: object, title: str) -> dict[str, object]:
    response = client.post(
        f"/api/diagram-sets/{diagram_set_id}/diagrams",
        data={"title": title, "kind": "flowchart"},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.django_db
def test_diagram_set_exposes_diagrams_through_nested_resources() -> None:
    client = Client()
    first_set = create_diagram_set(client, "First topic")
    second_set = create_diagram_set(client, "Second topic")
    first_diagram = create_diagram(client, first_set["id"], "First diagram")
    second_diagram = create_diagram(client, second_set["id"], "Second diagram")

    diagram_set = client.get(f"/api/diagram-sets/{first_set['id']}")
    collection = client.get(f"/api/diagram-sets/{first_set['id']}/diagrams")
    detail = client.get(f"/api/diagram-sets/{first_set['id']}/diagrams/{first_diagram['id']}")
    global_collection = client.get("/api/diagrams")
    global_detail = client.get(f"/api/diagrams/{first_diagram['id']}")

    assert diagram_set.status_code == 200
    assert "diagrams" not in diagram_set.json()
    assert collection.status_code == 200
    assert [diagram["id"] for diagram in collection.json()] == [first_diagram["id"]]
    assert second_diagram["id"] not in [diagram["id"] for diagram in collection.json()]
    assert detail.status_code == 200
    assert detail.json() == first_diagram
    assert global_collection.status_code == 200
    assert {diagram["id"] for diagram in global_collection.json()} == {
        first_diagram["id"],
        second_diagram["id"],
    }
    assert global_detail.status_code == 200
    assert global_detail.json() == first_diagram


@pytest.mark.django_db
def test_nested_diagram_detail_rejects_a_diagram_from_another_set() -> None:
    client = Client()
    first_set = create_diagram_set(client, "First topic")
    second_set = create_diagram_set(client, "Second topic")
    diagram = create_diagram(client, second_set["id"], "Second diagram")

    response = client.get(f"/api/diagram-sets/{first_set['id']}/diagrams/{diagram['id']}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_nested_diagram_collection_rejects_an_unknown_set() -> None:
    response = Client().get("/api/diagram-sets/missing/diagrams")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}
