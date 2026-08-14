import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.fixture
def client() -> Client:
    return Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)


@pytest.fixture
def scaffolding_payload() -> dict[str, object]:
    return {
        "language_id": "python",
        "name": "Package",
        "description": "Creates a Python package.",
        "spec": {
            "language": "python",
            "variables": [],
            "templates": [
                {
                    "path": "src/package/__init__.py",
                    "content": "",
                    "write_mode": "overwrite",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_siren_discovers_and_creates_scaffoldings(
    client: Client,
    scaffolding_payload: dict[str, object],
) -> None:
    root = client.get("/siren/")

    assert root.status_code == 200
    assert root["Content-Type"] == SIREN_MEDIA_TYPE
    assert root.json()["class"] == ["api", "entry-point"]
    assert {link["href"] for link in root.json()["links"]} >= {"http://testserver/siren/scaffoldings"}

    collection = client.get("/siren/scaffoldings")

    assert collection.status_code == 200
    assert collection["Content-Type"] == SIREN_MEDIA_TYPE
    assert collection.json()["class"] == ["collection", "scaffolding"]
    action = next(action for action in collection.json()["actions"] if action["name"] == "create_scaffolding")
    assert action["href"] == "http://testserver/siren/scaffoldings"
    assert action["method"] == "POST"
    assert [field["name"] for field in action["fields"]] == ["language_id", "name", "description"]
    structured_form = action["https://modwire.dev/siren/structured-form/v1"]
    assert structured_form["version"] == "1"
    assert structured_form["controls"][0]["name"] == "spec"
    assert structured_form["controls"][0]["schema"]["type"] == "object"

    created = client.post(
        action["href"].removeprefix("http://testserver"),
        data=scaffolding_payload,
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created["Content-Type"] == SIREN_MEDIA_TYPE
    assert created.json()["class"] == ["scaffolding"]
    assert created.json()["properties"]["name"] == "Package"

    details = client.get(f"/siren/scaffoldings/{created.json()['properties']['id']}")

    assert details.status_code == 200
    assert details["Content-Type"] == SIREN_MEDIA_TYPE
    assert details.json()["class"] == ["scaffolding"]
    assert {action["name"] for action in details.json()["actions"]} == {
        "delete_scaffolding",
        "get_scaffolding",
        "render_scaffolding",
        "update_scaffolding",
    }

    action = next(action for action in details.json()["actions"] if action["name"] == "update_scaffolding")
    updated = client.put(
        action["href"].removeprefix("http://testserver"),
        data={**scaffolding_payload, "name": "Updated package"},
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated["Content-Type"] == SIREN_MEDIA_TYPE
    assert updated.json()["class"] == ["scaffolding"]
    assert updated.json()["properties"]["name"] == "Updated package"

    action = next(action for action in details.json()["actions"] if action["name"] == "render_scaffolding")
    assert action["href"] == (
        f"http://testserver/siren/scaffoldings/{created.json()['properties']['id']}/renderings"
    )
    assert action["method"] == "POST"
    rendering = client.post(
        action["href"].removeprefix("http://testserver"),
        data={"parameters": {}},
        content_type="application/json",
    )

    assert rendering.status_code == 200
    assert rendering["Content-Type"] == SIREN_MEDIA_TYPE
    assert rendering.json()["class"] == ["command-result"]
    assert rendering.json()["properties"] == {"files": {"src/package/__init__.py": ""}}

    action = next(action for action in details.json()["actions"] if action["name"] == "delete_scaffolding")
    deleted = client.delete(action["href"].removeprefix("http://testserver"))

    assert deleted.status_code == 204
    assert deleted["Content-Type"] == SIREN_MEDIA_TYPE


def test_siren_preserves_ordinary_json_without_siren_negotiation() -> None:
    response = Client().get("/api/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["title"] == "Enclosure API"
    assert "Accept" in response["Vary"]


@pytest.mark.django_db
def test_siren_projects_missing_resources_as_errors(client: Client) -> None:
    response = client.get("/siren/scaffoldings/missing")

    assert response.status_code == 404
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {"detail": "Resource not found.", "status": 404}
    assert response.json()["links"][0]["href"] == "http://testserver/siren/scaffoldings/missing"


@pytest.mark.django_db
def test_siren_projects_validation_errors(client: Client) -> None:
    response = client.post("/siren/scaffoldings", data={}, content_type="application/json")

    assert response.status_code == 422
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {
        "detail": [
            {"type": "missing", "loc": ["body", "body", "language_id"], "msg": "Field required"},
            {"type": "missing", "loc": ["body", "body", "name"], "msg": "Field required"},
            {"type": "missing", "loc": ["body", "body", "description"], "msg": "Field required"},
            {"type": "missing", "loc": ["body", "body", "spec"], "msg": "Field required"},
        ],
        "status": 422,
    }
