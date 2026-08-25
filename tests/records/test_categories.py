import pytest
from django.test import Client

from enclosure.records.models import Category, CategorySchemaRevision

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


@pytest.mark.django_db
def test_create_category_starts_schema_history_at_version_one() -> None:
    category = create_category(Client())

    assert category["schema_version"] == 1
    assert category["content_schema"] == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **INITIAL_SCHEMA,
    }
    revision = CategorySchemaRevision.objects.get(category_id=category["id"], version=1)
    assert revision.content_schema == category["content_schema"]


@pytest.mark.django_db
def test_category_list_returns_references_without_content_schemas() -> None:
    client = Client()
    category = create_category(client)

    response = client.get("/api/records/categories")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": category["id"],
            "title": category["title"],
            "schema_version": category["schema_version"],
        }
    ]
    details = client.get(f"/api/records/categories/{category['id']}")
    assert details.status_code == 200
    assert details.json()["content_schema"] == category["content_schema"]


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
    assert response.json()["version"] == 1
    stored = Category.objects.get(pk=category["id"])
    assert stored.schema_version == 1
    assert stored.content_schema == response.json()["content_schema"]
    assert list(stored.schema_revisions.order_by("version").values_list("version", flat=True)) == [1]


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
    stored = Category.objects.get(pk=category["id"])
    assert stored.schema_version == 2
    assert list(stored.schema_revisions.order_by("version").values_list("version", flat=True)) == [1, 2]


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
    stored = Category.objects.get(pk=category["id"])
    assert stored.schema_version == category["schema_version"]
    assert stored.content_schema == category["content_schema"]
