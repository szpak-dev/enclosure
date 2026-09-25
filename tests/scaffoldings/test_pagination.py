import pytest
from django.test import Client


@pytest.mark.django_db
def test_scaffolding_catalogue_and_rendering_manifests_are_bounded() -> None:
    client = Client()
    ids = []
    for index in range(3):
        created = client.post(
            "/api/scaffoldings",
            data={
                "language_id": "python",
                "name": f"Package {index}",
                "description": "Pagination fixture.",
                "spec": {
                    "language": "python",
                    "variables": [],
                    "templates": [
                        {"path": f"{index}.txt", "content": str(index), "write_mode": "overwrite"},
                        {"path": f"{index}.md", "content": str(index), "write_mode": "overwrite"},
                    ],
                },
            },
            content_type="application/json",
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])

    first = client.get("/api/scaffoldings", data={"offset": 0, "limit": 2}).json()
    final = client.get(
        "/api/scaffoldings",
        data={"offset": first["next_offset"], "limit": first["limit"]},
    ).json()
    empty = client.get(
        "/api/scaffoldings",
        data={"offset": final["next_offset"], "limit": final["limit"]},
    ).json()

    assert len(first["items"]) == 2
    assert first["has_more"] is True
    assert len(final["items"]) == 1
    assert final["has_more"] is False
    assert empty["items"] == []

    rendering = client.post(
        f"/api/scaffoldings/{ids[0]}/renderings",
        data={"parameters": {}, "offset": 0, "limit": 1},
        content_type="application/json",
    ).json()
    assert len(rendering["items"]) == 1
    assert rendering["has_more"] is True
    assert set(rendering["items"][0]) == {"path", "overwrite", "size_bytes", "revision", "preview"}

    search = client.post(
        "/api/scaffoldings/name-search-results",
        data={"name": "Package", "limit": 1},
        content_type="application/json",
    ).json()
    assert len(search) == 1


def test_sirenity_owns_scaffolding_manifest_navigation_links() -> None:
    schema = Client().get("/api/openapi.json").json()
    detail = schema["paths"]["/api/scaffoldings/{scaffolding_id}"]["get"]
    manifests = schema["paths"]["/api/scaffoldings/{scaffolding_id}/template-manifests"]["get"]

    assert set(detail["responses"]["200"]["links"]) == {"template_manifests"}
    assert manifests["responses"]["200"]["links"] == {
        "next": {
            "operationId": "read_scaffolding_template_manifests",
            "parameters": {
                "offset": "$response.body#/next_offset",
                "limit": "$response.body#/limit",
            },
            "x-sirenity": {
                "sourceInputs": {
                    "scaffolding_id": "$request.path.scaffolding_id",
                    "expected_revision": "$request.query.expected_revision",
                }
            },
        },
        "template": {
            "operationId": "read_scaffolding_template",
            "parameters": {
                "query.path": "$response.body#/path",
                "query.expected_revision": "$response.body#/revision",
            },
            "x-sirenity": {
                "rel": "item",
                "scope": "entity",
                "itemCollection": "$response.body#/items",
                "sourceInputs": {"scaffolding_id": "$request.path.scaffolding_id"},
            },
        },
    }
