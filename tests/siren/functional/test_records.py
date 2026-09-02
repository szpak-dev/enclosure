import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.mark.django_db
def test_siren_projects_an_empty_tag_collection() -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get("/siren/records/tags")

    assert response.status_code == 200
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["collection", "tag"]
    assert response.json().get("entities", []) == []


@pytest.mark.django_db
def test_siren_searches_records() -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).post(
        "/siren/records/search-results",
        data={"query": "missing", "limit": 5},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["collection", "search-result"]
    assert response.json().get("entities", []) == []


@pytest.mark.django_db
def test_siren_exposes_schema_update_as_a_separate_category_action() -> None:
    client = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)
    created = client.post(
        "/siren/records/categories",
        data={"title": "Example", "content_schema": {"type": "object"}},
        content_type="application/json",
    )
    assert created.status_code == 201
    category_id = created.json()["properties"]["id"]

    details = client.get(f"/siren/records/categories/{category_id}")

    assert details.status_code == 200
    actions = {action["name"]: action for action in details.json()["actions"]}
    assert [field["name"] for field in actions["update_record_category"]["fields"]] == ["title"]
    schema_action = actions["update_record_category_content_schema"]
    assert schema_action["href"] == (f"http://testserver/siren/records/categories/{category_id}/content-schema")
    assert schema_action["method"] == "PUT"
    structured_form = schema_action["https://modwire.dev/siren/structured-form/v1"]
    assert [control["name"] for control in structured_form["controls"]] == ["content_schema"]


@pytest.mark.django_db
def test_siren_schema_update_of_missing_category_returns_not_found() -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).put(
        "/siren/records/categories/missing/content-schema",
        data={"content_schema": {"type": "object"}},
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {"detail": "Resource not found.", "status": 404}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/siren/records/missing",
        "/siren/records/categories/missing",
        "/siren/records/tags/missing",
    ],
)
def test_siren_projects_missing_records_as_not_found(path: str) -> None:
    response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get(path)

    assert response.status_code == 404
    assert response["Content-Type"] == SIREN_MEDIA_TYPE
    assert response.json()["class"] == ["error"]
    assert response.json()["properties"] == {"detail": "Resource not found.", "status": 404}
