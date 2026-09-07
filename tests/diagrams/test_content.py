import json

import pytest
from django.test import Client


def create_renderable_diagram(client: Client) -> dict[str, object]:
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Content reads", "description": "Bounded content verification."},
        content_type="application/json",
    ).json()
    diagram = client.post(
        f"/api/diagram-sets/{diagram_set['id']}/diagrams",
        data={"title": "Content flow", "kind": "flowchart"},
        content_type="application/json",
    ).json()
    for operation, arguments in (
        ("add_start", {"id": "start", "label": "Start"}),
        ("add_end", {"id": "end", "label": "End"}),
        ("add_flow", {"id": "flow", "source_id": "start", "target_id": "end"}),
    ):
        response = client.post(
            f"/api/diagrams/{diagram['id']}/commands",
            data={
                "expected_revision": diagram["revision"],
                "operation": operation,
                "arguments": arguments,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        diagram = response.json()
    return diagram


@pytest.mark.django_db
def test_reads_revision_pinned_source_and_canonical_snapshot_pages() -> None:
    client = Client()
    diagram = create_renderable_diagram(client)

    source = client.get(
        f"/api/diagrams/{diagram['id']}/content",
        data={"document": "source", "expected_revision": diagram["revision"], "offset": 0, "limit": 12},
    )
    snapshot = client.get(
        f"/api/diagrams/{diagram['id']}/content",
        data={"document": "snapshot", "expected_revision": diagram["revision"], "offset": 0, "limit": 512},
    )

    assert source.status_code == 200
    assert source.json() == {
        "diagram_id": diagram["id"],
        "revision": diagram["revision"],
        "document": "source",
        "offset": 0,
        "limit": 12,
        "total_characters": len(diagram["source"]),
        "content": diagram["source"][:12],
        "has_more": len(diagram["source"]) > 12,
        "next_offset": min(12, len(diagram["source"])),
    }
    canonical_snapshot = json.dumps(
        diagram["snapshot"],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert snapshot.status_code == 200
    assert snapshot.json()["content"] == canonical_snapshot[:512]
    assert snapshot.json()["total_characters"] == len(canonical_snapshot)
    assert snapshot.json()["next_offset"] == min(512, len(canonical_snapshot))


@pytest.mark.django_db
def test_rejected_content_reads_do_not_change_the_diagram() -> None:
    client = Client()
    diagram = create_renderable_diagram(client)
    before = client.get(f"/api/diagrams/{diagram['id']}").json()

    stale = client.get(
        f"/api/diagrams/{diagram['id']}/content",
        data={"document": "source", "expected_revision": diagram["revision"] - 1, "offset": 0, "limit": 12},
    )
    oversized = client.get(
        f"/api/diagrams/{diagram['id']}/content",
        data={"document": "snapshot", "expected_revision": diagram["revision"], "offset": 0, "limit": 513},
    )
    outside = client.get(
        f"/api/diagrams/{diagram['id']}/content",
        data={
            "document": "source",
            "expected_revision": diagram["revision"],
            "offset": len(diagram["source"]) + 1,
            "limit": 1,
        },
    )

    assert stale.status_code == 422
    assert stale.json() == {"detail": "Diagram changed; get it again before reading content."}
    assert oversized.status_code == 422
    assert outside.status_code == 422
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == before
