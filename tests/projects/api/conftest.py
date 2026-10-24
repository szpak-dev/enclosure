import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def dependencies(client: Client) -> dict[str, str]:
    category = client.post(
        "/api/records/categories",
        data={"title": "Project context", "content_schema": {"type": "object"}},
        content_type="application/json",
    )
    assert category.status_code == 201

    tag = client.post(
        "/api/records/tags",
        data={"name": "project"},
        content_type="application/json",
    )
    assert tag.status_code == 201

    record = client.post(
        "/api/records",
        data={
            "title": "Project context",
            "content": {},
            "category_id": category.json()["id"],
            "tag_ids": [tag.json()["id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert record.status_code == 201

    scaffolding = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Project package",
            "description": "Creates a project package.",
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
        },
        content_type="application/json",
    )
    assert scaffolding.status_code == 201

    return {
        "category_id": category.json()["id"],
        "record_id": record.json()["id"],
        "scaffolding_id": scaffolding.json()["id"],
        "tag_id": tag.json()["id"],
    }
