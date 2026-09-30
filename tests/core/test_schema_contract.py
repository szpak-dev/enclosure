import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_unknown_input_field_is_rejected_without_creating_a_diagram_set() -> None:
    client = Client()

    response = client.post(
        "/api/diagram-sets",
        data={
            "title": "Example diagram set",
            "description": "Example strict-schema input.",
            "example_unknown": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert client.get("/api/diagram-sets").json()["items"] == []


def test_incomplete_input_is_rejected_without_creating_a_diagram_set() -> None:
    client = Client()

    response = client.post(
        "/api/diagram-sets",
        data={"description": "Example input without the required title."},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert client.get("/api/diagram-sets").json()["items"] == []


def test_invalid_nested_input_is_rejected_without_creating_a_scaffolding() -> None:
    client = Client()

    response = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Example scaffolding",
            "description": "Example nested strict-schema input.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [],
                "example_unknown": True,
            },
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert client.get("/api/scaffoldings").json()["items"] == []


def test_in_scope_input_and_output_contracts_are_closed_in_openapi() -> None:
    schema = Client().get("/api/openapi.json").json()
    contract_names = (
        "CreateCategory",
        "Category",
        "RegisterProject",
        "Project",
        "CreateDiagram",
        "Diagram",
        "ScaffoldingInput",
        "Scaffolding",
    )

    assert all(schema["components"]["schemas"][name]["additionalProperties"] is False for name in contract_names)
