from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


def test_siren_discovers_and_lists_languages() -> None:
    client = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)

    root = client.get("/siren/")
    collection_link = next(
        link
        for link in root.json()["links"]
        if link["rel"] == ["collection"] and link["href"].endswith("/siren/languages")
    )
    response = client.get("/siren/languages")

    assert collection_link["title"] == "Language"
    assert response.status_code == 200
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["collection", "language"]
    assert [entity["properties"]["id"] for entity in response.json()["entities"]] == [
        "markdown",
        "mermaid",
        "php",
        "python",
        "typescript",
        "yaml",
    ]


def test_siren_gets_language_details() -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get("/siren/languages/python")

    assert response.status_code == 200
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["language"]
    assert response.json()["properties"] == {
        "id": "python",
        "name": "Python",
        "aliases": ["py"],
        "source_extensions": [".py"],
    }


def test_siren_projects_missing_language_as_not_found() -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get("/siren/languages/missing")

    assert response.status_code == 404
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {"detail": "Resource not found.", "status": 404}
