import asyncio
import json

import pytest

from .test_runtime import PublicCompositeApplication, PublicMcpClient


@pytest.mark.django_db(transaction=True)
def test_every_record_operation_has_a_complete_bounded_presentation() -> None:
    results = asyncio.run(PublicMcpClient(PublicCompositeApplication()).record_presentations())

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
        assert "content" not in data["resources"][0], operation
        assert results[operation].structured_content["follow_ups"][0]["operation_id"] == "read_record_resource"

    for operation in ("find_record_tags", "find_record_categories", "find_records"):
        data = results[operation].structured_content["data"]
        assert len(data["items"]) == 1, operation
        assert data["has_more"] is True, operation
        assert results[operation].structured_content["follow_ups"] == [
            {
                "operation_id": operation,
                "arguments": {"offset": data["next_offset"], "limit": data["limit"]},
            }
        ]

    schema_page = results["read_record_category_content_schema"].structured_content
    assert schema_page["data"]["has_more"] is True
    assert schema_page["follow_ups"][0]["operation_id"] == "read_record_category_content_schema"

    resource_page = results["read_record_resource"].structured_content
    assert resource_page["data"]["path"] == "guidance/record.py"
    assert resource_page["data"]["has_more"] is True
    assert resource_page["follow_ups"][0]["operation_id"] == "read_record_resource"
