from collections.abc import Callable

import pytest
from django.test import Client

from .test_api import create_diagram_set

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("layout", ("elk", "dagre"))
def test_exported_class_labels_fit_after_fonts_load(
    client: Client, measure_snapshot_labels: Callable[[dict[str, object]], dict[str, list[str]]], layout: str
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
    diagram = client.get(f"/api/diagrams/{receipt['diagram_id']}").json()
    result = measure_snapshot_labels(diagram["snapshot"])
    assert len(result["labels"]) >= 5
    assert any("ExampleArchitectureReport" in label for label in result["labels"])
    assert result["clipped"] == []
    assert result["overlaps"] == []
