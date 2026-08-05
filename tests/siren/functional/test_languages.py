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
