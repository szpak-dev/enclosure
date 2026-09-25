import asyncio
import json

import pytest
from mcp.types import CallToolResult

from .test_runtime import ConfiguredApplication, PublicMcpClient


def assert_bounded(result: CallToolResult) -> None:
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


async def read_oversized_diagram_set_page() -> tuple[CallToolResult, CallToolResult, CallToolResult]:
    client = PublicMcpClient(ConfiguredApplication())
    async with client.session() as (session, _):
        await session.initialize()
        for index in range(25):
            created = await session.call_tool(
                "create_diagram_set",
                {
                    "title": f"Example diagram set {index:02d}",
                    "description": f"Example diagram set {index:02d}: " + "detail " * 80,
                },
            )
            assert created.is_error is False

        page = await session.call_tool("find_diagram_sets", {"offset": 0, "limit": 25})
        retry = page.structured_content["follow_ups"][0]
        retried = await session.call_tool(retry["operation_id"], retry["arguments"])
        final_retry = retried.structured_content["follow_ups"][0]
        final = await session.call_tool(final_retry["operation_id"], final_retry["arguments"])
        return page, retried, final


async def create_oversized_record() -> tuple[CallToolResult, CallToolResult]:
    client = PublicMcpClient(ConfiguredApplication())
    async with client.session() as (session, _):
        await session.initialize()
        tag = await session.call_tool("create_record_tag", {"name": "Example recovery tag"})
        category = await session.call_tool(
            "create_record_category",
            {
                "title": "Example recovery category",
                "content_schema": {"type": "object"},
            },
        )
        created = await session.call_tool(
            "create_record",
            {
                "title": "Example recovery record",
                "content": {f"detail_{index:02d}": "value " * 75 for index in range(14)},
                "category_id": category.structured_content["data"]["id"],
                "tag_ids": [tag.structured_content["data"]["id"]],
                "resources": [
                    {
                        "path": f"examples/resource_{index:02d}.py",
                        "language": "python",
                        "content": f"example_{index} = True\n",
                    }
                    for index in range(16)
                ],
            },
        )
        verified = await session.call_tool(
            "get_record",
            {"record_id": created.structured_content["data"]["id"]},
        )
        return created, verified


@pytest.mark.django_db(transaction=True)
def test_oversized_collection_returns_a_prefix_and_same_offset_retry() -> None:
    page, retried, final = asyncio.run(read_oversized_diagram_set_page())

    assert page.is_error is False
    assert page.structured_content["status"] == "incomplete"
    data = page.structured_content["data"]
    assert data["reason"] == "presentation_budget_exceeded"
    assert data["offset"] == 0
    assert data["requested_limit"] == 25
    assert data["retry_limit"] == 12
    assert data["count"] == 25
    assert data["returned_count"] == len(data["items"])
    assert 0 < data["returned_count"] < data["count"]
    assert len({item["id"] for item in data["items"]}) == data["returned_count"]
    assert all(item["title"].startswith("Example diagram set ") for item in data["items"])
    assert page.structured_content["follow_ups"] == [
        {
            "operation_id": "find_diagram_sets",
            "arguments": {"offset": 0, "limit": 12},
        }
    ]
    assert_bounded(page)

    assert retried.is_error is False
    assert retried.structured_content["status"] == "incomplete"
    assert retried.structured_content["data"]["requested_limit"] == 12
    assert retried.structured_content["data"]["retry_limit"] == 6
    assert retried.structured_content["follow_ups"] == [
        {
            "operation_id": "find_diagram_sets",
            "arguments": {"offset": 0, "limit": 6},
        }
    ]
    assert_bounded(retried)

    assert final.is_error is False
    assert final.structured_content["status"] == "ok"
    assert final.structured_content["data"]["count"] == 6
    assert_bounded(final)


@pytest.mark.django_db(transaction=True)
def test_oversized_mutation_stays_compact_and_recoverable() -> None:
    created, verified = asyncio.run(create_oversized_record())

    assert created.is_error is False
    assert created.structured_content["status"] == "ok"
    data = created.structured_content["data"]
    assert data["id"]
    assert data["content_revision"]
    assert data["resources_revision"]
    assert data["resource_count"] == 16
    assert "content" not in data
    assert "resources" not in data
    assert created.structured_content["follow_ups"] == [
        {"operation_id": "get_record", "arguments": {"record_id": data["id"]}}
    ]
    assert_bounded(created)

    assert verified.is_error is False
    assert verified.structured_content["status"] == "ok"
    assert verified.structured_content["data"]["id"] == data["id"]
    assert "content" not in verified.structured_content["data"]
    assert "resources" not in verified.structured_content["data"]
    assert {follow_up["operation_id"] for follow_up in verified.structured_content["follow_ups"]} == {
        "read_record_content",
        "read_record_resource_manifests",
    }
    assert_bounded(verified)


@pytest.mark.django_db(transaction=True)
def test_document_follow_up_uses_the_presentation_budget_and_reconstructs_exact_content() -> None:
    source = "example_value = 'bounded document content'\n" * 240

    async def exercise() -> tuple[CallToolResult, CallToolResult, list[CallToolResult]]:
        client = PublicMcpClient(ConfiguredApplication())
        async with client.session() as (session, http_client):
            await session.initialize()
            category = await session.call_tool(
                "create_record_category",
                {"title": "Example document category", "content_schema": {"type": "object"}},
            )
            tag = await session.call_tool("create_record_tag", {"name": "Example document tag"})
            created = await session.call_tool(
                "create_record",
                {
                    "title": "Example document record",
                    "content": {},
                    "category_id": category.structured_content["data"]["id"],
                    "tag_ids": [tag.structured_content["data"]["id"]],
                    "resources": [
                        {
                            "path": "examples/document.py",
                            "language": "python",
                            "content": "example_value = True\n",
                        }
                    ],
                },
            )
            assert created.is_error is False, json.dumps(created.structured_content, indent=2)
            assert created.structured_content["status"] == "ok", json.dumps(created.structured_content, indent=2)
            record_id = created.structured_content["data"]["id"]
            updated = await http_client.put(
                f"/api/records/{record_id}",
                json={
                    "title": "Example document record",
                    "content": {},
                    "category_id": category.structured_content["data"]["id"],
                    "tag_ids": [tag.structured_content["data"]["id"]],
                    "resources": [
                        {
                            "path": "examples/document.py",
                            "language": "python",
                            "content": source,
                        }
                    ],
                },
            )
            assert updated.status_code == 200
            record = await session.call_tool("get_record", {"record_id": record_id})
            manifest_follow_up = next(
                follow_up
                for follow_up in record.structured_content["follow_ups"]
                if follow_up["operation_id"] == "read_record_resource_manifests"
            )
            manifests = await session.call_tool(
                manifest_follow_up["operation_id"],
                manifest_follow_up["arguments"],
            )
            follow_up = next(
                follow_up
                for follow_up in manifests.structured_content["follow_ups"]
                if follow_up["operation_id"] == "read_record_resource"
            )
            pages = []
            while follow_up:
                page = await session.call_tool(follow_up["operation_id"], follow_up["arguments"])
                pages.append(page)
                follow_up = page.structured_content["follow_ups"]
                follow_up = follow_up[0] if follow_up else None
            return record, manifests, pages

    record, manifests, pages = asyncio.run(exercise())

    initial = next(
        follow_up
        for follow_up in record.structured_content["follow_ups"]
        if follow_up["operation_id"] == "read_record_resource_manifests"
    )
    assert initial["arguments"]["record_id"] == record.structured_content["data"]["id"]
    assert initial["arguments"]["expected_revision"]
    assert manifests.structured_content["data"]["items"][0]["path"] == "examples/document.py"
    assert all(page.is_error is False for page in pages)
    assert pages[0].structured_content["status"] == "incomplete"
    assert pages[0].structured_content["data"]["reason"] == "presentation_budget_exceeded"
    content_pages = [page for page in pages if page.structured_content["status"] == "ok"]
    assert "".join(page.structured_content["data"]["content"] for page in content_pages) == source
    assert content_pages[0].structured_content["data"]["offset"] == 0
    assert all(
        current.structured_content["data"]["next_offset"] == following.structured_content["data"]["offset"]
        for current, following in zip(content_pages, content_pages[1:])
    )
    assert content_pages[-1].structured_content["data"]["has_more"] is False
    for page in pages:
        assert_bounded(page)
