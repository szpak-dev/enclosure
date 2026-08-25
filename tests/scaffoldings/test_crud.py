import pytest
from django.test import Client


@pytest.mark.django_db
def test_scaffolding_crud() -> None:
    client = Client()
    payload = {
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

    created = client.post("/api/scaffoldings", data=payload, content_type="application/json")

    assert created.status_code == 201
    scaffolding_id = created.json()["id"]

    listed = client.get("/api/scaffoldings")

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == scaffolding_id

    fetched = client.get(f"/api/scaffoldings/{scaffolding_id}")

    assert fetched.status_code == 200
    assert fetched.json()["spec"] == payload["spec"]

    rendering = client.post(
        f"/api/scaffoldings/{scaffolding_id}/renderings",
        data={"parameters": {}},
        content_type="application/json",
    )

    assert rendering.status_code == 200
    assert rendering.json() == {"files": {"src/package/__init__.py": ""}}

    payload["name"] = "Renamed package"
    updated = client.put(f"/api/scaffoldings/{scaffolding_id}", data=payload, content_type="application/json")

    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed package"

    deleted = client.delete(f"/api/scaffoldings/{scaffolding_id}")

    assert deleted.status_code == 204


@pytest.mark.django_db
def test_search_scaffoldings_by_name_and_language() -> None:
    client = Client()
    python = {
        "language_id": "python",
        "name": "Package",
        "description": "Creates a Python package.",
        "spec": {"language": "python", "variables": [], "templates": []},
    }
    javascript = {
        "language_id": "javascript",
        "name": "Package",
        "description": "Creates a JavaScript package.",
        "spec": {"language": "javascript", "variables": [], "templates": []},
    }
    created = [
        client.post("/api/scaffoldings", data=payload, content_type="application/json")
        for payload in (python, javascript)
    ]
    assert all(response.status_code == 201 for response in created)

    matches = client.post(
        "/api/scaffoldings/name-search-results",
        data={"name": "ack"},
        content_type="application/json",
    )
    constrained = client.post(
        "/api/scaffoldings/name-search-results",
        data={"name": "Package", "language_id": "python"},
        content_type="application/json",
    )

    assert matches.status_code == 200
    assert {item["language_id"] for item in matches.json()} == {"python", "javascript"}
    assert constrained.status_code == 200
    assert constrained.json() == [
        {
            "id": created[0].json()["id"],
            "language_id": "python",
            "name": "Package",
            "description": "Creates a Python package.",
        }
    ]


@pytest.mark.django_db
def test_create_rejects_jinja_content_without_jinja_suffix() -> None:
    response = Client().post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Invalid template",
            "description": "A template with an invalid content suffix.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [
                    {
                        "path": "src/package/__init__.py",
                        "content": "Generated for {{ package_name }}.",
                        "write_mode": "overwrite",
                    },
                ],
            },
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Template content uses Jinja syntax; its path must end with '.jinja'."}


@pytest.mark.django_db
def test_render_rejects_invalid_parameter_types_with_scaffolding_error() -> None:
    created = Client().post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Typed template",
            "description": "A template with an integer parameter.",
            "spec": {
                "language": "python",
                "variables": [{"name": "count", "type": "integer"}],
                "templates": [{"path": "count.txt", "content": "", "write_mode": "overwrite"}],
            },
        },
        content_type="application/json",
    )

    assert created.status_code == 201

    response = Client().post(
        f"/api/scaffoldings/{created.json()['id']}/renderings",
        data={"parameters": {"count": "one"}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert "Input should be a valid integer" in response.json()["detail"]
