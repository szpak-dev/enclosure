from base64 import b64decode
from hashlib import sha256

import pytest
from django.test import Client

from .test_api import create_diagram, create_diagram_set
from .test_content import create_renderable_diagram

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"expected_revision": 0},
        {"expected_revision": "example-invalid"},
        {"expected_revision": 1, "offset": -1},
        {"expected_revision": 1, "limit": -1},
    ],
)
def test_png_rejects_invalid_query_without_changing_draft(query: dict[str, object]) -> None:
    client = Client(HTTP_ACCEPT="application/json")
    group = create_diagram_set(client, "Example PNG validation")
    diagram = create_diagram(client, group["id"], "Example draft")
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()

    assert client.get(f"{url}/png", query).status_code == 422
    assert client.get(url).json() == before


def test_png_rejects_unknown_diagram() -> None:
    assert Client().get("/api/diagrams/example-missing/png", {"expected_revision": 1}).status_code == 404


def test_png_rejects_draft_without_publishing_an_artifact() -> None:
    client = Client(HTTP_ACCEPT="application/json")
    group = create_diagram_set(client, "Example PNG draft")
    diagram = create_diagram(client, group["id"], "Example draft")
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()

    response = client.get(f"{url}/png", {"expected_revision": diagram["revision"]})

    assert response.status_code == 422
    assert response.json() == {"detail": "Diagram has no source to export."}
    assert client.get(url).json() == before


def test_png_rejects_stale_revision_before_serving_cached_content() -> None:
    client = Client(HTTP_ACCEPT="application/json")
    diagram = create_renderable_diagram(client)
    url = f"/api/diagrams/{diagram['id']}"
    original = client.get(f"{url}/png", {"expected_revision": diagram["revision"]})
    assert original.status_code == 200
    changed = client.post(
        f"{url}/commands",
        {
            "expected_revision": diagram["revision"],
            "operation": "update_element",
            "arguments": {"id": "start", "kind": "start", "changes": {"label": "Example changed start"}},
        },
        content_type="application/json",
    )
    assert changed.status_code == 200
    before = client.get(url).json()

    stale = client.get(f"{url}/png", {"expected_revision": diagram["revision"]})
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Diagram changed; reload it before downloading PNG."}
    assert client.get(url).json() == before

    current = client.get(f"{url}/png", {"expected_revision": before["revision"]})
    assert current.status_code == 200
    assert current.json()["content_revision"] != original.json()["content_revision"]
    assert current.json()["content"] != original.json()["content"]


@pytest.mark.parametrize("accept", (None, "*/*", "image/png"))
def test_png_download_matches_complete_json_artifact_without_changing_activity(accept: str | None) -> None:
    client = Client(HTTP_ACCEPT="application/json")
    diagram = create_renderable_diagram(client)
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()
    listing = client.get("/api/diagrams").json()
    query = {"expected_revision": diagram["revision"]}
    response = client.get(f"{url}/png", query)
    assert response.status_code == 200
    assert "Accept" in response.headers["Vary"]
    document = response.json()
    content = b64decode(document["content"], validate=True)
    assert content[:8] == b"\x89PNG\r\n\x1a\n"
    assert document["diagram_id"] == diagram["id"]
    assert document["revision"] == diagram["revision"]
    assert document["filename"] == f"diagram-{diagram['id']}-r{diagram['revision']}.png"
    assert document["media_type"] == "image/png"
    assert document["total_bytes"] == len(content)
    assert document["width"] == int.from_bytes(content[16:20], "big") > 0
    assert document["height"] == int.from_bytes(content[20:24], "big") > 0
    assert document["content_revision"] == sha256(content).hexdigest()
    assert not {"offset", "limit", "has_more", "next_offset"} & document.keys()

    binary_client = Client() if accept is None else Client(HTTP_ACCEPT=accept)
    binary = binary_client.get(f"{url}/png", query)
    assert binary.status_code == 200
    assert binary.content == content
    assert binary.headers["Content-Type"] == "image/png"
    assert binary.headers["Content-Disposition"] == f'attachment; filename="{document["filename"]}"'
    assert binary.headers["ETag"] == f'"{document["content_revision"]}"'
    assert "Accept" in binary.headers["Vary"]
    assert client.get(f"{url}/png", query).json() == document
    assert client.get(url).json() == before
    assert client.get("/api/diagrams").json() == listing
    assert client.get(f"{url}/svg", query).status_code == 404


def test_png_is_discoverable_from_both_siren_details_and_openapi() -> None:
    client = Client(HTTP_ACCEPT="application/json")
    diagram = create_renderable_diagram(client)
    siren = Client(HTTP_ACCEPT="application/vnd.siren+json")
    for path in (
        f"/siren/diagrams/{diagram['id']}",
        f"/siren/diagram-sets/{diagram['diagram_set_id']}/diagrams/{diagram['id']}",
    ):
        detail = siren.get(path).json()
        download = next(link for link in detail["links"] if "enclosure:download-png" in link["rel"])
        assert f"/siren/diagrams/{diagram['id']}/png?" in download["href"]
        assert f"expected_revision={diagram['revision']}" in download["href"]
        response = siren.get(download["href"])
        assert response.status_code == 200
        assert "Accept" in response.headers["Vary"]
        assert response.json()["properties"]["media_type"] == "image/png"
        assert not any("next" in link["rel"] for link in response.json().get("links", []))
    paths = client.get("/api/openapi.json").json()["paths"]
    operation = paths["/api/diagrams/{diagram_id}/png"]["get"]
    assert operation["operationId"] == "download_diagram_png"
    assert "application/json" in operation["responses"]["200"]["content"]
    assert "/api/diagrams/{diagram_id}/svg" not in paths
