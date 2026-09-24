import hashlib
import json

import pytest
from django.test import Client

from enclosure.records.models import CategorySchemaRevision


@pytest.mark.django_db
def test_record_detail_exposes_a_manifest_and_reads_one_exact_resource_in_pages() -> None:
    client = Client()
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
    source = "line = 'record resource'\n" * 30
    created = client.post(
        "/api/records",
        data={
            "title": "Example record",
            "content": {},
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
            "resources": [{"path": "docs/example.py", "language": "python", "content": source}],
        },
        content_type="application/json",
    )

    assert created.status_code == 201
    record = created.json()
    manifest = record["resources"][0]
    assert manifest == {
        "path": "docs/example.py",
        "language": "python",
        "media_type": "text/x-python",
        "size_bytes": len(source.encode()),
        "revision": hashlib.sha256(source.encode()).hexdigest(),
    }
    assert "content" not in manifest

    canonical_content = json.dumps(record["content"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert record["content_revision"] == hashlib.sha256(canonical_content.encode()).hexdigest()
    assert record["content_total_characters"] == len(canonical_content)
    content = client.get(
        f"/api/records/{record['id']}/content",
        {"expected_revision": record["content_revision"]},
    )
    manifests = client.get(
        f"/api/records/{record['id']}/resource-manifests",
        {"expected_revision": record["resources_revision"]},
    )
    assert content.status_code == 200
    assert content.json()["content"] == canonical_content
    assert content.json()["limit"] == len(canonical_content)
    assert manifests.status_code == 200
    assert manifests.json()["items"] == record["resources"]
    assert manifests.json()["total"] == record["resource_count"] == 1
    assert manifests.json()["has_more"] is False

    first = client.get(
        f"/api/records/{record['id']}/resources/content",
        {
            "path": manifest["path"],
            "expected_revision": manifest["revision"],
            "offset": 0,
            "limit": 512,
        },
    )
    second = client.get(
        f"/api/records/{record['id']}/resources/content",
        {
            "path": manifest["path"],
            "expected_revision": manifest["revision"],
            "offset": first.json()["next_offset"],
            "limit": 512,
        },
    )

    assert first.status_code == 200
    assert first.json()["has_more"] is True
    assert second.status_code == 200
    assert second.json()["has_more"] is False
    assert first.json()["content"] + second.json()["content"] == source
    stale = client.get(
        f"/api/records/{record['id']}/resources/content",
        {
            "path": manifest["path"],
            "expected_revision": "0" * 64,
            "offset": 0,
            "limit": 512,
        },
    )
    assert stale.status_code == 422


@pytest.mark.django_db
def test_category_detail_exposes_a_manifest_and_reads_the_canonical_schema() -> None:
    client = Client()
    response = client.post(
        "/api/records/categories",
        data={
            "title": "Oversized schema",
            "content_schema": {
                "type": "object",
                "properties": {f"field_{index}": {"type": "string"} for index in range(40)},
            },
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    category = response.json()
    revision = CategorySchemaRevision.objects.get(category_id=category["id"], version=1)
    canonical = json.dumps(revision.content_schema, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert category["content_schema_revision"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert category["content_schema_size_bytes"] == len(canonical.encode())
    assert "content_schema" not in category

    content = ""
    offset = 0
    while True:
        page = client.get(
            f"/api/records/categories/{category['id']}/content-schema",
            {
                "schema_version": 1,
                "expected_revision": category["content_schema_revision"],
                "offset": offset,
                "limit": 512,
            },
        )
        assert page.status_code == 200
        content += page.json()["content"]
        if not page.json()["has_more"]:
            break
        offset = page.json()["next_offset"]

    assert content == canonical
