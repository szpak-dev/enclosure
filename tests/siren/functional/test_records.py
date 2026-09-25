from urllib.parse import parse_qs, urlsplit

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
def test_siren_links_record_detail_to_canonical_content_and_resource_items() -> None:
    client = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)
    category = client.post(
        "/siren/records/categories",
        data={"title": "Recovery", "content_schema": {"type": "object"}},
        content_type="application/json",
    ).json()["properties"]
    tag = client.post(
        "/siren/records/tags",
        data={"name": "recovery"},
        content_type="application/json",
    ).json()["properties"]
    created = client.post(
        "/siren/records",
        data={
            "title": "Recovery record",
            "content": {"purpose": "typed navigation"},
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
            "resources": [
                {"path": "first.py", "language": "python", "content": "first = True\n"},
                {"path": "second.py", "language": "python", "content": "second = True\n"},
            ],
        },
        content_type="application/json",
    )
    record_id = created.json()["properties"]["id"]

    detail = client.get(f"/siren/records/{record_id}")
    links = detail.json()["links"]
    manifests_link = next(link for link in links if urlsplit(link["href"]).path.endswith("/resource-manifests"))
    content_action = next(action for action in detail.json()["actions"] if action["name"] == "read_record_content")

    canonical = client.get(
        urlsplit(content_action["href"]).path,
        data={"expected_revision": detail.json()["properties"]["content_revision"]},
    )
    assert canonical.status_code == 200
    assert '"purpose":"typed navigation"' in canonical.json()["properties"]["content"]
    manifests = client.get(
        urlsplit(manifests_link["href"]).path,
        data={
            "expected_revision": detail.json()["properties"]["resources_revision"],
            "offset": 0,
            "limit": 1,
        },
    )
    assert manifests.status_code == 200
    assert "collection" in manifests.json()["class"]
    assert len(manifests.json()["entities"]) == 1
    resource = manifests.json()["entities"][0]
    resource_link = next(link for link in resource["links"] if "item" in link["rel"])
    resource_query = parse_qs(urlsplit(resource_link["href"]).query)
    assert resource_query["path"] == [resource["properties"]["path"]]
    assert resource_query["expected_revision"] == [resource["properties"]["revision"]]
    assert any(link["rel"] == ["next"] for link in manifests.json()["links"])

    content = client.get(urlsplit(resource_link["href"]).path, data=resource_query)
    assert content.status_code == 200
    assert content.json()["properties"]["content"] == "first = True\n"


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
