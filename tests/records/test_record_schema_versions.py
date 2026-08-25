import pytest
from django.test import Client

NAME_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}
COUNT_SCHEMA = {
    "type": "object",
    "properties": {"count": {"type": "integer"}},
    "required": ["count"],
    "additionalProperties": False,
}


def create_category(client: Client, title: str, content_schema: dict) -> dict:
    response = client.post(
        "/api/records/categories",
        data={"title": title, "content_schema": content_schema},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def create_tag(client: Client) -> dict:
    response = client.post(
        "/api/records/tags",
        data={"name": "Example"},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def write_record(category_id: str, tag_id: str, content: dict) -> dict:
    return {
        "title": "Example",
        "content": content,
        "category_id": category_id,
        "tag_ids": [tag_id],
        "resources": [],
    }


@pytest.mark.django_db
def test_new_record_is_assigned_current_schema_version() -> None:
    client = Client()
    category = create_category(client, "Names", NAME_SCHEMA)
    tag = create_tag(client)

    response = client.post(
        "/api/records",
        data=write_record(category["id"], tag["id"], {"name": "value"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    record = response.json()
    assert record["schema_version"] == 1
    assert record["category"] == {
        "id": category["id"],
        "title": category["title"],
        "schema_version": category["schema_version"],
    }


@pytest.mark.django_db
def test_record_responses_do_not_embed_the_category_content_schema() -> None:
    client = Client()
    category = create_category(client, "Names", NAME_SCHEMA)
    tag = create_tag(client)
    created = client.post(
        "/api/records",
        data=write_record(category["id"], tag["id"], {"name": "value"}),
        content_type="application/json",
    ).json()

    responses = (
        client.get("/api/records"),
        client.get(f"/api/records/{created['id']}"),
    )

    for response in responses:
        assert response.status_code == 200
        record = response.json()[0] if isinstance(response.json(), list) else response.json()
        assert "content_schema" not in record["category"]


@pytest.mark.django_db
def test_update_record_validates_against_its_stored_schema_version() -> None:
    client = Client()
    category = create_category(client, "Names", NAME_SCHEMA)
    tag = create_tag(client)
    created = client.post(
        "/api/records",
        data=write_record(category["id"], tag["id"], {"name": "initial"}),
        content_type="application/json",
    ).json()
    schema_update = client.put(
        f"/api/records/categories/{category['id']}/content-schema",
        data={"content_schema": COUNT_SCHEMA},
        content_type="application/json",
    )
    assert schema_update.status_code == 200

    valid = client.put(
        f"/api/records/{created['id']}",
        data=write_record(category["id"], tag["id"], {"name": "updated"}),
        content_type="application/json",
    )
    invalid = client.put(
        f"/api/records/{created['id']}",
        data=write_record(category["id"], tag["id"], {"count": 1}),
        content_type="application/json",
    )

    assert valid.status_code == 200
    assert valid.json()["schema_version"] == 1
    assert invalid.status_code == 422


@pytest.mark.django_db
def test_new_record_uses_latest_schema_version() -> None:
    client = Client()
    category = create_category(client, "Values", NAME_SCHEMA)
    tag = create_tag(client)
    first = client.post(
        "/api/records",
        data=write_record(category["id"], tag["id"], {"name": "initial"}),
        content_type="application/json",
    )
    assert first.status_code == 201
    schema_update = client.put(
        f"/api/records/categories/{category['id']}/content-schema",
        data={"content_schema": COUNT_SCHEMA},
        content_type="application/json",
    )
    assert schema_update.status_code == 200

    response = client.post(
        "/api/records",
        data=write_record(category["id"], tag["id"], {"count": 1}),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["schema_version"] == 2


@pytest.mark.django_db
def test_change_record_category_assigns_destination_schema_version() -> None:
    client = Client()
    source = create_category(client, "Source", NAME_SCHEMA)
    destination = create_category(client, "Destination", NAME_SCHEMA)
    tag = create_tag(client)
    source_record = client.post(
        "/api/records",
        data=write_record(source["id"], tag["id"], {"name": "source"}),
        content_type="application/json",
    ).json()
    destination_record = client.post(
        "/api/records",
        data=write_record(destination["id"], tag["id"], {"name": "destination"}),
        content_type="application/json",
    )
    assert destination_record.status_code == 201
    schema_update = client.put(
        f"/api/records/categories/{destination['id']}/content-schema",
        data={"content_schema": COUNT_SCHEMA},
        content_type="application/json",
    )
    assert schema_update.status_code == 200

    response = client.put(
        f"/api/records/{source_record['id']}",
        data=write_record(destination["id"], tag["id"], {"count": 1}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["category"]["id"] == destination["id"]
    assert response.json()["schema_version"] == 2
