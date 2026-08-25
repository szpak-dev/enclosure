import pytest
from django.test import Client


def create_record_with_resource(client: Client) -> dict:
    category = client.post(
        "/api/records/categories",
        data={"title": "Example", "content_schema": {"type": "object"}},
        content_type="application/json",
    ).json()
    tag = client.post(
        "/api/records/tags",
        data={"name": "Example"},
        content_type="application/json",
    ).json()
    response = client.post(
        "/api/records",
        data={
            "title": "Example record",
            "content": {},
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
            "resources": [
                {
                    "path": "example.py",
                    "language": "python",
                    "content": 'source = "very large source content"',
                }
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.django_db
def test_search_records_returns_an_empty_collection() -> None:
    response = Client().post(
        "/api/records/search-results",
        data={"query": "missing", "limit": 5},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_search_records_returns_summaries_without_resource_content() -> None:
    client = Client()
    record = create_record_with_resource(client)

    response = client.post(
        "/api/records/search-results",
        data={"query": "Example", "limit": 5},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": record["id"],
            "title": "Example record",
            "category": record["category"],
            "schema_version": record["schema_version"],
            "tags": record["tags"],
        }
    ]
