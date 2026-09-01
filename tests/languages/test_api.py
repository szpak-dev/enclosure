from django.test import Client

from enclosure.shared.diagrams import DiagramsError, DiagramsService


def test_lists_supported_languages() -> None:
    response = Client().get("/api/languages")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "markdown",
            "name": "Markdown",
            "aliases": [],
            "source_extensions": [".md"],
        },
        {
            "id": "mermaid",
            "name": "Mermaid",
            "aliases": [],
            "source_extensions": [".mermaid", ".mmd"],
        },
        {
            "id": "php",
            "name": "PHP",
            "aliases": [],
            "source_extensions": [".php"],
        },
        {
            "id": "python",
            "name": "Python",
            "aliases": ["py"],
            "source_extensions": [".py"],
        },
        {
            "id": "typescript",
            "name": "TypeScript",
            "aliases": ["ts"],
            "source_extensions": [".tsx", ".ts", ".jsx", ".js"],
        },
        {
            "id": "yaml",
            "name": "Yaml",
            "aliases": [],
            "source_extensions": [".yml", ".yaml"],
        },
    ]


def test_gets_supported_language() -> None:
    response = Client().get("/api/languages/python")

    assert response.status_code == 200
    assert response.json() == {
        "id": "python",
        "name": "Python",
        "aliases": ["py"],
        "source_extensions": [".py"],
    }


def test_missing_language_returns_not_found() -> None:
    response = Client().get("/api/languages/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


def test_gets_mermaid_configuration_schema_from_public_command_catalog() -> None:
    schema = DiagramsService().get_schema("flowchart")

    assert schema["type"] == "object"
    assert schema["properties"]["wrap"]["type"] == "boolean"


def test_mermaid_configuration_schema_rejects_unknown_diagram() -> None:
    try:
        DiagramsService().get_schema("missing")
    except DiagramsError as error:
        assert str(error) == "Unsupported diagram ID: 'missing'"
    else:
        raise AssertionError("Unknown diagram ID was accepted.")
