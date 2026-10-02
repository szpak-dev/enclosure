import pytest
from django.test import Client


def create_dependencies(client: Client) -> tuple[dict, dict]:
    category_response = client.post(
        "/api/records/categories",
        data={
            "title": "Validated records",
            "content_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        content_type="application/json",
    )
    tag_response = client.post(
        "/api/records/tags",
        data={"name": "Validated"},
        content_type="application/json",
    )
    assert category_response.status_code == 201
    assert tag_response.status_code == 201
    return category_response.json(), tag_response.json()


def record_input(category_id: str, tag_id: str) -> dict:
    return {
        "title": "Validated record",
        "content": {"name": "value"},
        "category_id": category_id,
        "tag_ids": [tag_id],
        "resources": [
            {
                "path": "records/example.py",
                "language": "python",
                "content": "value = 1\n",
            }
        ],
    }


@pytest.mark.django_db
@pytest.mark.parametrize("duplicate", ["tag", "resource"])
def test_structurally_invalid_record_input_creates_no_record(duplicate: str) -> None:
    client = Client()
    category, tag = create_dependencies(client)
    data = record_input(category["id"], tag["id"])
    if duplicate == "tag":
        data["tag_ids"] = [tag["id"], tag["id"]]
    else:
        data["resources"] = [data["resources"][0], data["resources"][0]]

    response = client.post(
        "/api/records",
        data=data,
        content_type="application/json",
    )

    assert response.status_code == 422
    records = client.get("/api/records")
    assert records.status_code == 200
    assert records.json()["items"] == []


@pytest.mark.django_db
def test_invalid_source_collection_creates_no_record() -> None:
    client = Client()
    category, tag = create_dependencies(client)
    data = record_input(category["id"], tag["id"])
    data["resources"].append(
        {
            "path": "records/unsupported.source",
            "language": "unsupported-language",
            "content": "not supported",
        }
    )

    response = client.post(
        "/api/records",
        data=data,
        content_type="application/json",
    )

    assert response.status_code == 404
    records = client.get("/api/records")
    assert records.status_code == 200
    assert records.json()["items"] == []


@pytest.mark.django_db
def test_structurally_invalid_replacement_leaves_record_unchanged() -> None:
    client = Client()
    category, tag = create_dependencies(client)
    data = record_input(category["id"], tag["id"])
    created = client.post(
        "/api/records",
        data=data,
        content_type="application/json",
    )
    assert created.status_code == 201
    original = created.json()
    data["title"] = "Rejected replacement"
    data["resources"] = [data["resources"][0], data["resources"][0]]

    response = client.put(
        f"/api/records/{original['id']}",
        data=data,
        content_type="application/json",
    )

    assert response.status_code == 422
    stored = client.get(f"/api/records/{original['id']}")
    assert stored.status_code == 200
    assert stored.json() == original
