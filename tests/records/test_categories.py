import hashlib
import json

import pytest
from django.test import Client

INITIAL_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}
NEXT_SCHEMA = {
    "type": "object",
    "properties": {"count": {"type": "integer"}},
    "required": ["count"],
    "additionalProperties": False,
}


def create_category(client: Client) -> dict:
    response = client.post(
        "/api/records/categories",
        data={"title": "Example", "content_schema": INITIAL_SCHEMA},
        content_type="application/json",
    )

    assert response.status_code == 201
    return response.json()


def read_schema(client: Client, category: dict, version: int | None = None) -> dict:
    schema_version = version or category["schema_version"]
    response = client.get(
        f"/api/records/categories/{category['id']}/content-schema",
        {
            "schema_version": schema_version,
            "expected_revision": category["content_schema_revision"],
            "offset": 0,
            "limit": category["content_schema_size_bytes"],
        },
    )
    assert response.status_code == 200
    return json.loads(response.json()["content"])


@pytest.mark.django_db
def test_create_category_starts_schema_history_at_version_one() -> None:
    client = Client()
    category = create_category(client)

    assert category["schema_version"] == 1
    content_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **INITIAL_SCHEMA,
    }
    canonical = json.dumps(content_schema, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert category["content_schema_revision"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert category["content_schema_size_bytes"] == len(canonical.encode())
    assert read_schema(client, category) == content_schema


@pytest.mark.django_db
def test_category_list_returns_references_without_content_schemas() -> None:
    client = Client()
    category = create_category(client)

    response = client.get("/api/records/categories")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": category["id"],
                "title": category["title"],
                "schema_version": category["schema_version"],
            }
        ],
        "has_more": False,
        "next_offset": 1,
        "limit": 50,
    }
    details = client.get(f"/api/records/categories/{category['id']}")
    assert details.status_code == 200
    assert "content_schema" not in details.json()
    assert details.json()["content_schema_revision"] == category["content_schema_revision"]


@pytest.mark.django_db
def test_update_schema_without_records_replaces_version_one() -> None:
    client = Client()
    category = create_category(client)

    response = client.put(
        f"/api/records/categories/{category['id']}/content-schema",
        data={"content_schema": NEXT_SCHEMA},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["category_id"] == category["id"]
    assert response.json()["version"] == 1
    stored = client.get(f"/api/records/categories/{category['id']}")
    assert stored.status_code == 200
    assert stored.json()["schema_version"] == 1
    assert read_schema(client, stored.json()) == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **NEXT_SCHEMA,
    }
    missing_version = client.get(
        f"/api/records/categories/{category['id']}/content-schema",
        {
            "schema_version": 2,
            "expected_revision": stored.json()["content_schema_revision"],
            "offset": 0,
            "limit": 512,
        },
    )
    assert missing_version.status_code == 404


@pytest.mark.django_db
def test_update_schema_with_records_publishes_next_version() -> None:
    client = Client()
    category = create_category(client)
    tag = client.post(
        "/api/records/tags",
        data={"name": "Example"},
        content_type="application/json",
    ).json()
    record = client.post(
        "/api/records",
        data={
            "title": "Example",
            "content": {"name": "value"},
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert record.status_code == 201

    response = client.put(
        f"/api/records/categories/{category['id']}/content-schema",
        data={"content_schema": NEXT_SCHEMA},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    stored = client.get(f"/api/records/categories/{category['id']}")
    assert stored.status_code == 200
    assert stored.json()["schema_version"] == 2
    original = read_schema(client, category, version=1)
    current = read_schema(client, stored.json(), version=2)
    assert original == {"$schema": "https://json-schema.org/draft/2020-12/schema", **INITIAL_SCHEMA}
    assert current == {"$schema": "https://json-schema.org/draft/2020-12/schema", **NEXT_SCHEMA}


@pytest.mark.django_db
def test_update_category_changes_only_its_title() -> None:
    client = Client()
    category = create_category(client)

    response = client.put(
        f"/api/records/categories/{category['id']}",
        data={"title": "Renamed"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {**category, "title": "Renamed"}


@pytest.mark.django_db
def test_invalid_schema_does_not_change_category() -> None:
    client = Client()
    category = create_category(client)

    response = client.put(
        f"/api/records/categories/{category['id']}/content-schema",
        data={"content_schema": {"type": "missing"}},
        content_type="application/json",
    )

    assert response.status_code == 422
    stored = client.get(f"/api/records/categories/{category['id']}")
    assert stored.status_code == 200
    assert stored.json()["schema_version"] == category["schema_version"]
    assert read_schema(client, stored.json()) == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **INITIAL_SCHEMA,
    }
