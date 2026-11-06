from collections.abc import Callable
from hashlib import sha256
from xml.etree import ElementTree

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
def test_svg_rejects_invalid_query_without_changing_draft(query: dict[str, object]) -> None:
    client = Client()
    group = create_diagram_set(client, "Example SVG validation")
    diagram = create_diagram(client, group["id"], "Example draft")
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()

    assert client.get(f"{url}/svg", query).status_code == 422
    assert client.get(url).json() == before


def test_svg_rejects_unknown_diagram() -> None:
    assert Client().get("/api/diagrams/example-missing/svg", {"expected_revision": 1}).status_code == 404


def test_svg_rejects_draft_without_publishing_an_artifact() -> None:
    client = Client()
    group = create_diagram_set(client, "Example SVG draft")
    diagram = create_diagram(client, group["id"], "Example draft")
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()

    response = client.get(f"{url}/svg", {"expected_revision": diagram["revision"]})

    assert response.status_code == 422
    assert response.json() == {"detail": "Diagram has no source to export."}
    assert client.get(url).json() == before


def test_svg_rejects_stale_revision_before_serving_cached_content() -> None:
    client = Client()
    diagram = create_renderable_diagram(client)
    url = f"/api/diagrams/{diagram['id']}"
    original = client.get(f"{url}/svg", {"expected_revision": diagram["revision"]})
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

    stale = client.get(f"{url}/svg", {"expected_revision": diagram["revision"]})
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Diagram changed; reload it before downloading SVG."}
    assert client.get(url).json() == before

    current = client.get(f"{url}/svg", {"expected_revision": before["revision"]})
    assert current.status_code == 200
    assert current.json()["content_revision"] != original.json()["content_revision"]
    assert "Example changed start" in current.json()["content"]


def test_svg_pages_reconstruct_one_immutable_download_without_changing_activity() -> None:
    client = Client()
    diagram = create_renderable_diagram(client)
    url = f"/api/diagrams/{diagram['id']}"
    before = client.get(url).json()
    listing = client.get("/api/diagrams").json()
    query = {"expected_revision": diagram["revision"]}
    response = client.get(f"{url}/svg", query)
    assert response.status_code == 200
    document = response.json()
    assert document["diagram_id"] == diagram["id"]
    assert document["revision"] == diagram["revision"]
    assert document["filename"] == f"diagram-{diagram['id']}-r{diagram['revision']}.svg"
    assert document["media_type"] == "image/svg+xml"
    assert document["offset"] == 0
    assert document["has_more"] is False
    assert document["limit"] == document["next_offset"] == document["total_characters"] == len(document["content"])
    assert document["content_revision"] == sha256(document["content"].encode()).hexdigest()
    svg = ElementTree.fromstring(document["content"])
    assert svg.tag == "{http://www.w3.org/2000/svg}svg"
    assert svg.attrib["viewBox"]

    outside = client.get(f"{url}/svg", {**query, "offset": document["total_characters"] + 1})
    assert outside.status_code == 422
    assert outside.json() == {"detail": "SVG content offset is outside the document."}
    end = client.get(f"{url}/svg", {**query, "offset": document["total_characters"]}).json()
    assert end["content"] == ""
    assert end["has_more"] is False
    assert end["limit"] > 0

    parts: list[str] = []
    offset = 0
    while offset < document["total_characters"]:
        page = client.get(f"{url}/svg", {**query, "offset": offset, "limit": 2048})
        assert page.status_code == 200
        payload = page.json()
        assert payload["content_revision"] == document["content_revision"]
        assert payload["offset"] == offset
        assert payload["next_offset"] == offset + len(payload["content"])
        assert payload["next_offset"] > offset
        assert payload["has_more"] == (payload["next_offset"] < document["total_characters"])
        parts.append(payload["content"])
        offset = payload["next_offset"]
    assert "".join(parts) == document["content"]
    assert client.get(f"{url}/svg", query).json() == document
    assert client.get(url).json() == before
    assert client.get("/api/diagrams").json() == listing


def test_svg_is_discoverable_from_both_siren_details_and_openapi() -> None:
    client = Client()
    diagram = create_renderable_diagram(client)
    siren = Client(HTTP_ACCEPT="application/vnd.siren+json")
    for path in (
        f"/siren/diagrams/{diagram['id']}",
        f"/siren/diagram-sets/{diagram['diagram_set_id']}/diagrams/{diagram['id']}",
    ):
        detail = siren.get(path).json()
        download = next(link for link in detail["links"] if "enclosure:download-svg" in link["rel"])
        assert f"/siren/diagrams/{diagram['id']}/svg?" in download["href"]
        assert f"expected_revision={diagram['revision']}" in download["href"]
        response = siren.get(download["href"] + "&limit=32")
        assert response.status_code == 200
        assert response.json()["properties"]["next_offset"] == 32
        continuation = next(link for link in response.json()["links"] if "next" in link["rel"])
        following = siren.get(continuation["href"])
        assert following.status_code == 200
        assert following.json()["properties"]["offset"] == 32
    operation = client.get("/api/openapi.json").json()["paths"]["/api/diagrams/{diagram_id}/svg"]["get"]
    assert operation["operationId"] == "download_diagram_svg"


@pytest.mark.parametrize("layout", ("elk", "dagre"))
def test_exported_class_labels_fit_after_fonts_load(
    client: Client, measure_svg: Callable[[str], dict[str, list[str]]], layout: str
) -> None:
    group = create_diagram_set(client, "Example long UML labels")
    created = client.post(
        f"/api/diagram-sets/{group['id']}/diagram-batches",
        data={
            "title": "Example architecture inspection",
            "kind": "classDiagram",
            "commands": [
                {"operation": "configure", "arguments": {"layout": layout, "wrap": True}},
                {
                    "operation": "add_class",
                    "arguments": {
                        "id": "example-inspection-service",
                        "label": "ExampleArchitectureInspectionService",
                        "attributes": [
                            {"name": "configuration_store", "type": {"name": "ExampleArchitectureConfigurationStore"}}
                        ],
                        "methods": [
                            {
                                "name": name,
                                "parameters": [
                                    {"name": "architecture_map", "type": {"name": "ExampleArchitectureMap"}},
                                    {"name": "configuration", "type": {"name": "ExampleArchitectureConfiguration"}},
                                ],
                                "return_type": {"name": "ExampleArchitectureReport"},
                            }
                            for name in ("collect", "collect_expanded_architecture_analysis", "review")
                        ],
                    },
                },
            ],
        },
        content_type="application/json",
    )
    assert created.status_code == 201, created.json()
    receipt = created.json()
    exported = client.get(f"/api/diagrams/{receipt['diagram_id']}/svg", {"expected_revision": receipt["revision"]})
    assert exported.status_code == 200, exported.json()
    document = exported.json()
    assert document["has_more"] is False
    result = measure_svg(document["content"])
    assert len(result["labels"]) >= 5
    assert any("ExampleArchitectureReport" in label for label in result["labels"])
    assert result["clipped"] == []
    assert result["overlaps"] == []
