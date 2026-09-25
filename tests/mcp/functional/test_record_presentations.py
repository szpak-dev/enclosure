import asyncio
import json

import pytest

from .test_runtime import ConfiguredApplication, PublicMcpClient


@pytest.mark.django_db(transaction=True)
def test_every_record_operation_has_a_complete_bounded_presentation() -> None:
    results = asyncio.run(PublicMcpClient(ConfiguredApplication()).record_presentations())

    assert set(results) == {
        "create_record_tag",
        "find_record_tags",
        "get_record_tag",
        "update_record_tag",
        "delete_record_tag",
        "create_record_category",
        "find_record_categories",
        "get_record_category",
        "update_record_category",
        "update_record_category_content_schema",
        "delete_record_category",
        "read_record_category_content_schema",
        "create_record",
        "find_records",
        "search_records",
        "get_record",
        "update_record",
        "delete_record",
        "read_record_content",
        "read_record_resource_manifests",
        "read_record_resource",
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

    for operation in ("create_record", "get_record", "update_record"):
        data = results[operation].structured_content["data"]
        assert "content" not in data, operation
        assert "resources" not in data, operation
        assert data["content_revision"], operation
        assert data["resources_revision"], operation
        assert data["resource_count"] == 1, operation

    detail_follow_ups = results["get_record"].structured_content["follow_ups"]
    assert {follow_up["operation_id"] for follow_up in detail_follow_ups} == {
        "read_record_content",
        "read_record_resource_manifests",
    }
    assert all(
        follow_up["arguments"]["record_id"] == results["get_record"].structured_content["data"]["id"]
        for follow_up in detail_follow_ups
    )
    assert all(follow_up["arguments"]["expected_revision"] for follow_up in detail_follow_ups)

    for operation in (
        "create_record_category",
        "get_record_category",
        "update_record_category_content_schema",
    ):
        follow_up = results[operation].structured_content["follow_ups"][0]
        assert follow_up["operation_id"] == "read_record_category_content_schema"
        assert follow_up["arguments"]["limit"] == 4096

    item_operations = {
        "find_record_tags": "get_record_tag",
        "find_record_categories": "get_record_category",
        "find_records": "get_record",
    }
    for operation, item_operation in item_operations.items():
        data = results[operation].structured_content["data"]
        assert len(data["items"]) == 1, operation
        assert data["has_more"] is True, operation
        follow_ups = results[operation].structured_content["follow_ups"]
        assert [follow_up for follow_up in follow_ups if follow_up["operation_id"] == operation] == [
            {
                "operation_id": operation,
                "arguments": {"offset": data["next_offset"], "limit": data["limit"]},
            }
        ]
        assert any(follow_up["operation_id"] == item_operation for follow_up in follow_ups)

    schema_page = results["read_record_category_content_schema"].structured_content
    assert schema_page["data"]["has_more"] is True
    assert schema_page["follow_ups"][0]["operation_id"] == "read_record_category_content_schema"

    content_page = results["read_record_content"].structured_content
    assert content_page["data"]["has_more"] is False
    assert content_page["data"]["content"] == '{"headline":"Revised","summary":"Verified"}'

    manifest_page = results["read_record_resource_manifests"].structured_content
    assert manifest_page["data"]["items"][0]["path"] == "guidance/record.py"
    assert manifest_page["data"]["has_more"] is False
    assert manifest_page["follow_ups"][0]["operation_id"] == "read_record_resource"

    resource_page = results["read_record_resource"].structured_content
    assert resource_page["data"]["path"] == "guidance/record.py"
    assert resource_page["data"]["has_more"] is True
    assert resource_page["follow_ups"][0]["operation_id"] == "read_record_resource"
