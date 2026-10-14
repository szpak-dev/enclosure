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


@pytest.mark.django_db
def test_record_creation_attacks_leave_public_state_empty_and_the_corrected_request_recovers() -> None:
    client = Client()
    category, tag = create_dependencies(client)
    valid = record_input(category["id"], tag["id"])
    attacks = (
        {**valid, "unexpected": True},
        {
            **valid,
            "resources": [{**valid["resources"][0], "unexpected": True}],
        },
        {**valid, "content": {"name": 7}},
        {**valid, "tag_ids": ["missing"]},
        {
            **valid,
            "resources": [
                {
                    "path": "records/unsupported.source",
                    "language": "unsupported-language",
                    "content": "not supported",
                }
            ],
        },
    )

    responses = [client.post("/api/records", data=attack, content_type="application/json") for attack in attacks]

    assert [response.status_code for response in responses] == [422, 422, 422, 404, 404]
    assert client.get("/api/records").json()["items"] == []

    recovered = client.post("/api/records", data=valid, content_type="application/json")

    assert recovered.status_code == 201
    assert [item["id"] for item in client.get("/api/records").json()["items"]] == [recovered.json()["id"]]
    assert client.get(f"/api/records/{recovered.json()['id']}").json() == recovered.json()


@pytest.mark.django_db
def test_record_replacement_attack_preserves_complete_public_state_and_the_corrected_request_recovers() -> None:
    client = Client()
    category, tag = create_dependencies(client)
    created = client.post(
        "/api/records",
        data=record_input(category["id"], tag["id"]),
        content_type="application/json",
    )
    assert created.status_code == 201
    original = created.json()
    valid = record_input(category["id"], tag["id"])
    valid["title"] = "Recovered replacement"

    rejected = client.put(
        f"/api/records/{original['id']}",
        data={**valid, "content": {"name": 7}},
        content_type="application/json",
    )

    assert rejected.status_code == 422
    assert client.get(f"/api/records/{original['id']}").json() == original
    assert [item["id"] for item in client.get("/api/records").json()["items"]] == [original["id"]]

    recovered = client.put(
        f"/api/records/{original['id']}",
        data=valid,
        content_type="application/json",
    )

    assert recovered.status_code == 200
    assert recovered.json()["title"] == "Recovered replacement"
    assert [item["id"] for item in client.get("/api/records").json()["items"]] == [original["id"]]


@pytest.mark.django_db
def test_record_catalogue_attacks_preserve_every_public_resource() -> None:
    client = Client()
    category, tag = create_dependencies(client)
    category_url = f"/api/records/categories/{category['id']}"
    tag_url = f"/api/records/tags/{tag['id']}"
    category_before = client.get(category_url).json()
    tag_before = client.get(tag_url).json()
    categories_before = client.get("/api/records/categories").json()
    tags_before = client.get("/api/records/tags").json()

    responses = (
        client.post(
            "/api/records/categories",
            data={"title": "Rejected category", "content_schema": {"type": "object"}, "unexpected": True},
            content_type="application/json",
        ),
        client.put(
            category_url,
            data={"title": "Rejected category update", "unexpected": True},
            content_type="application/json",
        ),
        client.put(
            f"{category_url}/content-schema",
            data={"content_schema": {"type": "object"}, "unexpected": True},
            content_type="application/json",
        ),
        client.post(
            "/api/records/tags",
            data={"name": "rejected-tag", "unexpected": True},
            content_type="application/json",
        ),
        client.put(
            tag_url,
            data={"name": "rejected-tag-update", "unexpected": True},
            content_type="application/json",
        ),
    )

    assert [response.status_code for response in responses] == [422] * len(responses)
    assert client.get(category_url).json() == category_before
    assert client.get(tag_url).json() == tag_before
    assert client.get("/api/records/categories").json() == categories_before
    assert client.get("/api/records/tags").json() == tags_before
