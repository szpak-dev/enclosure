import pytest
from django.test import Client

CRUD_COMMANDS = {
    "update_element",
    "update_relation",
    "update_annotation",
    "move_element",
    "reorder_elements",
    "remove_element",
    "remove_relation",
    "remove_annotation",
}


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


def test_diagram_kind_exposes_crud_commands_and_placements() -> None:
    response = Client().get("/api/diagrams/kinds/flowchart")

    assert response.status_code == 200
    description = response.json()
    assert CRUD_COMMANDS <= description["commands"].keys()
    assert description["placements"]["flow_group"]["allowed_parents"] == ["$root", "flow_group"]


@pytest.mark.django_db
def test_draft_survives_independent_commands_until_diagram_is_renderable() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Draft persistence")
    diagram = create_diagram(client, diagram_set["id"], "Draft flow")
    diagram_url = f"/api/diagrams/{diagram['id']}"

    assert diagram["snapshot"]["draft"] is True
    assert diagram["source"] == ""

    start = client.post(
        f"{diagram_url}/commands",
        data={
            "expected_revision": 1,
            "operation": "add_start",
            "arguments": {"id": "start", "label": "Start"},
        },
        content_type="application/json",
    )
    assert start.status_code == 200
    assert start.json()["revision"] == 2
    assert start.json()["snapshot"]["draft"] is True
    assert start.json()["source"] == ""

    end = client.post(
        f"{diagram_url}/commands",
        data={
            "expected_revision": 2,
            "operation": "add_end",
            "arguments": {"id": "end", "label": "End"},
        },
        content_type="application/json",
    )
    assert end.status_code == 200
    assert end.json()["revision"] == 3
    assert end.json()["snapshot"]["draft"] is True
    assert end.json()["source"] == ""

    flow = client.post(
        f"{diagram_url}/commands",
        data={
            "expected_revision": 3,
            "operation": "add_flow",
            "arguments": {"id": "flow", "source_id": "start", "target_id": "end"},
        },
        content_type="application/json",
    )
    assert flow.status_code == 200
    assert flow.json()["revision"] == 4
    assert flow.json()["snapshot"]["draft"] is False
    assert "flowchart TD" in flow.json()["source"]


@pytest.mark.django_db
def test_applies_an_ordered_command_batch_with_one_revision_and_a_compact_receipt() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Batch persistence")
    diagram = create_diagram(client, diagram_set["id"], "Batch flow")

    response = client.post(
        f"/api/diagrams/{diagram['id']}/command-batches",
        data={
            "expected_revision": diagram["revision"],
            "commands": [
                {"operation": "add_start", "arguments": {"id": "start", "label": "Start"}},
                {"operation": "add_end", "arguments": {"id": "end", "label": "End"}},
                {
                    "operation": "add_flow",
                    "arguments": {"id": "flow", "source_id": "start", "target_id": "end"},
                },
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "diagram_id": diagram["id"],
        "revision": diagram["revision"] + 1,
        "applied_count": 3,
    }
    stored = client.get(f"/api/diagrams/{diagram['id']}").json()
    assert stored["revision"] == diagram["revision"] + 1
    assert stored["snapshot"]["draft"] is False
    assert "flowchart TD" in stored["source"]


@pytest.mark.django_db
def test_accepts_hundreds_of_commands_in_one_bounded_request() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Large batch")
    diagram = create_diagram(client, diagram_set["id"], "Large draft")
    commands = [
        {"operation": "add_node", "arguments": {"id": f"node-{index}", "label": f"Node {index}"}}
        for index in range(250)
    ]

    response = client.post(
        f"/api/diagrams/{diagram['id']}/command-batches",
        data={"expected_revision": diagram["revision"], "commands": commands},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["applied_count"] == 250
    assert response.json()["revision"] == diagram["revision"] + 1


@pytest.mark.django_db
def test_rejected_command_batch_reports_the_index_and_preserves_the_diagram() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Batch rollback")
    diagram = create_diagram(client, diagram_set["id"], "Rollback flow")

    response = client.post(
        f"/api/diagrams/{diagram['id']}/command-batches",
        data={
            "expected_revision": diagram["revision"],
            "commands": [
                {"operation": "add_start", "arguments": {"id": "start", "label": "Start"}},
                {"operation": "missing", "arguments": {}},
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert "index 1" in response.json()["detail"]
    assert "operation 'missing'" in response.json()["detail"]
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == diagram


@pytest.mark.django_db
def test_rejects_command_batches_outside_the_public_size_bounds() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Batch bounds")
    diagram = create_diagram(client, diagram_set["id"], "Bounded flow")
    url = f"/api/diagrams/{diagram['id']}/command-batches"

    empty = client.post(
        url,
        data={"expected_revision": diagram["revision"], "commands": []},
        content_type="application/json",
    )
    oversized = client.post(
        url,
        data={
            "expected_revision": diagram["revision"],
            "commands": [{"operation": "add_node", "arguments": {}}] * 1001,
        },
        content_type="application/json",
    )

    assert empty.status_code == 422
    assert oversized.status_code == 422
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == diagram


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
    assert [diagram["id"] for diagram in collection.json()["items"]] == [first_diagram["id"]]
    assert second_diagram["id"] not in [diagram["id"] for diagram in collection.json()["items"]]
    assert detail.status_code == 200
    assert detail.json() == first_diagram
    assert global_collection.status_code == 200
    assert {diagram["id"] for diagram in global_collection.json()["items"]} == {
        first_diagram["id"],
        second_diagram["id"],
    }
    assert global_detail.status_code == 200
    assert global_detail.json() == first_diagram


@pytest.mark.django_db
def test_updates_diagram_title_without_changing_mermaiden_content() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Example metadata")
    diagram = create_diagram(client, diagram_set["id"], "Example original title")

    response = client.patch(
        f"/api/diagrams/{diagram['id']}",
        data={"expected_revision": diagram["revision"], "title": "Example updated title"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        **diagram,
        "title": "Example updated title",
        "revision": diagram["revision"] + 1,
        "updated_at": response.json()["updated_at"],
    }


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


@pytest.mark.django_db
def test_diagram_collections_are_deterministically_paginated() -> None:
    client = Client()
    diagram_sets = [create_diagram_set(client, f"Set {index}") for index in range(3)]
    diagram_set_id = diagram_sets[0]["id"]
    for index in range(3):
        create_diagram(client, diagram_set_id, f"Diagram {index}")

    paths = (
        "/api/diagram-sets",
        "/api/diagrams",
        f"/api/diagram-sets/{diagram_set_id}/diagrams",
    )
    for path in paths:
        first = client.get(path, {"offset": 0, "limit": 1})
        intermediate = client.get(path, {"offset": 1, "limit": 1})
        final = client.get(path, {"offset": 2, "limit": 1})
        empty = client.get(path, {"offset": 3, "limit": 1})

        assert first.status_code == 200
        assert len(first.json()["items"]) == 1
        assert first.json()["has_more"] is True
        assert first.json()["next_offset"] == 1
        assert first.json()["limit"] == 1
        assert intermediate.status_code == 200
        assert len(intermediate.json()["items"]) == 1
        assert intermediate.json()["has_more"] is True
        assert intermediate.json()["next_offset"] == 2
        assert intermediate.json()["limit"] == 1
        assert final.status_code == 200
        assert len(final.json()["items"]) == 1
        assert final.json()["has_more"] is False
        assert final.json()["next_offset"] == 3
        assert final.json()["limit"] == 1
        assert empty.status_code == 200
        assert empty.json() == {
            "items": [],
            "has_more": False,
            "next_offset": 3,
            "limit": 1,
        }


def test_sirenity_owns_diagram_collection_continuation_links() -> None:
    schema = Client().get("/api/openapi.json").json()
    paths = (
        "/api/diagram-sets",
        "/api/diagrams",
        "/api/diagram-sets/{diagram_set_id}/diagrams",
    )

    for path in paths:
        operation = schema["paths"][path]["get"]
        assert operation["responses"]["200"]["links"] == {
            "next": {
                "operationId": operation["operationId"],
                "parameters": {
                    "offset": "$response.body#/next_offset",
                    "limit": "$response.body#/limit",
                },
            }
        }


@pytest.mark.django_db
def test_diagram_collection_pagination_is_bounded() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Bounds")
    paths = (
        "/api/diagram-sets",
        "/api/diagrams",
        f"/api/diagram-sets/{diagram_set['id']}/diagrams",
    )

    for path in paths:
        assert client.get(path, {"offset": -1, "limit": 10}).status_code == 422
        assert client.get(path, {"offset": 0, "limit": 101}).status_code == 422
