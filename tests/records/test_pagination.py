import pytest
from django.test import Client


@pytest.mark.django_db
def test_record_collections_are_deterministically_paginated() -> None:
    client = Client()
    tags = [
        client.post(
            "/api/records/tags",
            data={"name": f"Tag {index}"},
            content_type="application/json",
        ).json()
        for index in range(3)
    ]
    categories = [
        client.post(
            "/api/records/categories",
            data={"title": f"Category {index}", "content_schema": {"type": "object"}},
            content_type="application/json",
        ).json()
        for index in range(3)
    ]
    for index, category in enumerate(categories):
        response = client.post(
            "/api/records",
            data={
                "title": f"Record {index}",
                "content": {},
                "category_id": category["id"],
                "tag_ids": [tags[0]["id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    for path in ("/api/records/tags", "/api/records/categories", "/api/records"):
        first = client.get(path, {"offset": 0, "limit": 1})
        intermediate = client.get(path, {"offset": 1, "limit": 1})
        final = client.get(path, {"offset": 2, "limit": 1})
        empty = client.get(path, {"offset": 3, "limit": 1})

        assert first.status_code == 200
        assert len(first.json()["items"]) == 1
        assert first.json()["has_more"] is True
        assert first.json()["next_offset"] == 1
        assert first.json()["limit"] == 1
        assert intermediate.status_code == 200
        assert len(intermediate.json()["items"]) == 1
        assert intermediate.json()["has_more"] is True
        assert intermediate.json()["next_offset"] == 2
        assert intermediate.json()["limit"] == 1
        assert final.status_code == 200
        assert len(final.json()["items"]) == 1
        assert final.json()["has_more"] is False
        assert final.json()["next_offset"] == 3
        assert final.json()["limit"] == 1
        assert empty.status_code == 200
        assert empty.json()["items"] == []
        assert empty.json()["has_more"] is False
        assert empty.json()["next_offset"] == 3
        assert empty.json()["limit"] == 1


def test_sirenity_owns_record_collection_continuation_links() -> None:
    schema = Client().get("/api/openapi.json").json()

    operations = {
        schema["paths"][path]["get"]["operationId"]: schema["paths"][path]["get"]
        for path in ("/api/records/tags", "/api/records/categories", "/api/records")
    }
    for operation_id, operation in operations.items():
        assert operation["responses"]["200"]["links"] == {
            "next": {
                "operationId": operation_id,
                "parameters": {
                    "offset": "$response.body#/next_offset",
                    "limit": "$response.body#/limit",
                },
            }
        }


def test_record_collection_pagination_is_bounded() -> None:
    client = Client()

    assert client.get("/api/records", {"offset": -1, "limit": 10}).status_code == 422
    assert client.get("/api/records", {"offset": 0, "limit": 101}).status_code == 422
