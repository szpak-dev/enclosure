from collections.abc import Mapping
from typing import Any

import pytest
from django.test import Client


def create_class_diagram(client: Client) -> dict[str, Any]:
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Service model", "description": "Class diagram command verification."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201

    response = client.post(
        f"/api/diagram-sets/{diagram_set.json()['id']}/diagrams",
        data={"title": "Service dependencies", "kind": "classDiagram"},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def apply_command(
    client: Client,
    diagram: Mapping[str, Any],
    operation: str,
    arguments: Mapping[str, object],
) -> dict[str, Any]:
    response = client.post(
        f"/api/diagrams/{diagram['id']}/commands",
        data={
            "expected_revision": diagram["revision"],
            "operation": operation,
            "arguments": arguments,
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    result = response.json()
    assert result["revision"] == diagram["revision"] + 1
    assert result["snapshot"]["version"] == 4
    return result


@pytest.mark.django_db
def test_all_class_diagram_commands_use_semantic_values_through_the_public_api() -> None:
    client = Client()
    description_response = client.get("/api/diagrams/kinds/classDiagram")

    assert description_response.status_code == 200
    commands = description_response.json()["commands"]
    assert set(commands) == {
        "add_class",
        "add_namespace",
        "add_note",
        "add_relation",
        "configure",
        "move_element",
        "remove_annotation",
        "remove_element",
        "remove_relation",
        "reorder_elements",
        "update_annotation",
        "update_element",
        "update_relation",
    }
    assert commands["add_class"]["$defs"]["Visibility"]["enum"] == [
        "public",
        "private",
        "protected",
        "package",
    ]
    assert commands["add_relation"]["$defs"]["ClassRelationKind"]["enum"] == [
        "association",
        "inheritance",
        "composition",
        "aggregation",
        "dependency",
        "realization",
    ]

    diagram = create_class_diagram(client)
    diagram = apply_command(client, diagram, "configure", {"wrap": True})
    diagram = apply_command(
        client,
        diagram,
        "add_namespace",
        {"id": "services", "label": "Services", "comment": "Application services"},
    )
    diagram = apply_command(
        client,
        diagram,
        "add_class",
        {
            "id": "catalog",
            "label": "CatalogService",
            "parent_id": "services",
            "attributes": [
                {
                    "name": "repository",
                    "type": {"name": "CatalogRepository"},
                    "visibility": "private",
                    "static": False,
                }
            ],
            "methods": [
                {
                    "name": "find",
                    "parameters": [{"name": "identifier", "type": {"name": "str"}}],
                    "return_type": {"name": "CatalogItem"},
                    "visibility": "public",
                    "modifier": "instance",
                }
            ],
            "annotations": ["injectable"],
            "comment": "Reads catalog items",
        },
    )
    diagram = apply_command(
        client,
        diagram,
        "add_class",
        {"id": "repository", "label": "CatalogRepository", "parent_id": "services"},
    )
    diagram = apply_command(
        client,
        diagram,
        "add_relation",
        {
            "id": "catalog_uses_repository",
            "source_id": "catalog",
            "target_id": "repository",
            "relation_kind": "dependency",
            "label": "uses",
        },
    )
    diagram = apply_command(
        client,
        diagram,
        "add_note",
        {"id": "catalog_note", "class_id": "catalog", "text": "Public query boundary"},
    )
    diagram = apply_command(
        client,
        diagram,
        "update_element",
        {"id": "catalog", "kind": "class", "changes": {"comment": "Queries catalog items"}},
    )
    diagram = apply_command(
        client,
        diagram,
        "update_relation",
        {
            "id": "catalog_uses_repository",
            "kind": "class_relation",
            "changes": {"relation_kind": "association", "label": "queries"},
        },
    )
    diagram = apply_command(
        client,
        diagram,
        "update_annotation",
        {
            "id": "catalog_note",
            "kind": "class_note",
            "changes": {
                "text": "Repository query boundary",
                "targets": [{"kind": "element", "id": "repository"}],
            },
        },
    )
    diagram = apply_command(
        client,
        diagram,
        "move_element",
        {"id": "catalog", "kind": "class", "parent_id": "", "position": 1},
    )
    diagram = apply_command(
        client,
        diagram,
        "reorder_elements",
        {"parent_id": "", "element_ids": ["services", "catalog"]},
    )
    diagram = apply_command(client, diagram, "remove_annotation", {"id": "catalog_note"})
    diagram = apply_command(client, diagram, "remove_relation", {"id": "catalog_uses_repository"})
    diagram = apply_command(client, diagram, "remove_element", {"id": "services", "cascade": True})

    assert diagram["snapshot"]["draft"] is False
    assert "classDiagram" in diagram["source"]
    assert "-CatalogRepository repository" in diagram["source"]
    assert "+find(str identifier) CatalogItem" in diagram["source"]


@pytest.mark.django_db
def test_rejected_class_diagram_commands_preserve_the_complete_resource() -> None:
    client = Client()
    diagram = create_class_diagram(client)
    diagram = apply_command(client, diagram, "add_class", {"id": "service", "label": "Service"})
    diagram = apply_command(client, diagram, "add_class", {"id": "repository", "label": "Repository"})
    before = client.get(f"/api/diagrams/{diagram['id']}").json()

    invalid_commands = (
        (
            "add_class",
            {"id": "injected\nclass Other", "label": "Injected"},
        ),
        (
            "add_class",
            {"id": "raw_member", "label": "RawMember", "attributes": ["+str value"]},
        ),
        (
            "add_relation",
            {
                "id": "raw_relation",
                "source_id": "service",
                "target_id": "repository",
                "relation_kind": "<|--",
            },
        ),
        ("remove_element", {"id": "service", "cascade": "false"}),
        ("move_element", {"id": "service", "kind": "class", "parent_id": "", "position": "0"}),
    )

    for operation, arguments in invalid_commands:
        response = client.post(
            f"/api/diagrams/{diagram['id']}/commands",
            data={
                "expected_revision": diagram["revision"],
                "operation": operation,
                "arguments": arguments,
            },
            content_type="application/json",
        )
        assert response.status_code == 422
        assert client.get(f"/api/diagrams/{diagram['id']}").json() == before
