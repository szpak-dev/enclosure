import asyncio
import json

import pytest

from .test_runtime import ConfiguredApplication, PublicMcpClient


@pytest.mark.django_db(transaction=True)
def test_every_scaffolding_operation_has_a_complete_bounded_presentation() -> None:
    results = asyncio.run(PublicMcpClient(ConfiguredApplication()).scaffolding_presentations())

    assert set(results) == {
        "create_scaffolding",
        "find_scaffoldings",
        "search_scaffoldings",
        "get_scaffolding",
        "update_scaffolding",
        "delete_scaffolding",
        "render_scaffolding",
        "read_scaffolding_template_manifests",
        "read_scaffolding_template",
        "read_scaffolding_rendered_file",
    }
    for operation, result in results.items():
        assert result.is_error is False, operation
        assert result.structured_content["operation_id"] == operation
        assert result.structured_content["status"] == "ok", json.dumps(
            {"operation": operation, "presentation": result.structured_content},
            indent=2,
        )
        assert result.structured_content["data"].get("reason") != "presentation_incomplete", operation
        assert len(result.content[0].text.encode("utf-8")) <= 16_384, operation
        assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192, operation

    for operation in ("create_scaffolding", "get_scaffolding", "update_scaffolding"):
        data = results[operation].structured_content["data"]
        assert "spec" not in data
        assert data["templates_revision"]
        assert data["template_count"] == 2

    detail_follow_ups = results["get_scaffolding"].structured_content["follow_ups"]
    assert detail_follow_ups[0]["operation_id"] == "read_scaffolding_template_manifests"
    assert (
        detail_follow_ups[0]["arguments"]["scaffolding_id"]
        == results["get_scaffolding"].structured_content["data"]["id"]
    )
    assert detail_follow_ups[0]["arguments"]["expected_revision"]

    catalogue = results["find_scaffoldings"].structured_content
    assert len(catalogue["data"]["items"]) == 1
    assert catalogue["data"]["has_more"] is True
    assert {follow_up["operation_id"] for follow_up in catalogue["follow_ups"]} == {
        "get_scaffolding",
        "find_scaffoldings",
    }

    manifests = results["read_scaffolding_template_manifests"].structured_content
    assert manifests["data"]["items"][0]["path"] == "README.md.jinja"
    assert manifests["data"]["has_more"] is True
    assert {follow_up["operation_id"] for follow_up in manifests["follow_ups"]} == {
        "read_scaffolding_template",
        "read_scaffolding_template_manifests",
    }

    template = results["read_scaffolding_template"].structured_content
    assert template["data"]["content"] == "# {{ name }}\n"
    assert template["data"]["has_more"] is False
    assert template["follow_ups"] == []

    rendering = results["render_scaffolding"].structured_content
    assert len(rendering["data"]["items"]) == 1
    assert rendering["data"]["has_more"] is True
    assert "content" not in rendering["data"]["items"][0]
    assert {follow_up["operation_id"] for follow_up in rendering["follow_ups"]} == {
        "read_scaffolding_rendered_file",
        "render_scaffolding",
    }
    content_follow_up = next(
        follow_up
        for follow_up in rendering["follow_ups"]
        if follow_up["operation_id"] == "read_scaffolding_rendered_file"
    )
    assert content_follow_up["arguments"]["limit"] == 4096

    rendered = results["read_scaffolding_rendered_file"].structured_content
    assert rendered["data"]["has_more"] is True
    assert rendered["follow_ups"][0]["operation_id"] == "read_scaffolding_rendered_file"
