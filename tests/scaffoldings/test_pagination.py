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
