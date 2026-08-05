from django.test import Client


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
