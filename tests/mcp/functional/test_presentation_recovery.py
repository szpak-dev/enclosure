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
        verification = created.structured_content["follow_ups"][0]
        verified = await session.call_tool(verification["operation_id"], verification["arguments"])
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
def test_oversized_mutation_returns_identity_and_verification() -> None:
    created, verified = asyncio.run(create_oversized_record())

    assert created.is_error is False
    assert created.structured_content["status"] == "incomplete"
    data = created.structured_content["data"]
    assert data["reason"] == "presentation_budget_exceeded"
    assert data["id"]
    assert data["resources"]
    assert all(resource["revision"] for resource in data["resources"])
    assert created.structured_content["follow_ups"] == [
        {
            "operation_id": "get_record",
            "arguments": {"record_id": data["id"]},
        }
    ]
    assert_bounded(created)

    assert verified.is_error is False
    assert verified.structured_content["status"] == "incomplete"
    assert verified.structured_content["data"]["reason"] == "presentation_budget_exceeded"
    assert verified.structured_content["data"]["id"] == data["id"]
    assert_bounded(verified)


@pytest.mark.django_db(transaction=True)
def test_document_follow_up_uses_the_presentation_budget_and_reconstructs_exact_content() -> None:
    source = "example_value = 'bounded document content'\n" * 240

    async def exercise() -> tuple[CallToolResult, list[CallToolResult]]:
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
            follow_up = record.structured_content["follow_ups"][0]
            pages = []
            while follow_up:
                page = await session.call_tool(follow_up["operation_id"], follow_up["arguments"])
                pages.append(page)
                follow_up = page.structured_content["follow_ups"]
                follow_up = follow_up[0] if follow_up else None
            return record, pages

    record, pages = asyncio.run(exercise())

    initial = record.structured_content["follow_ups"][0]
    assert initial["operation_id"] == "read_record_resource"
    assert initial["arguments"]["limit"] == 4096
    assert all(page.is_error is False for page in pages)
    assert all(page.structured_content["status"] == "ok" for page in pages)
    assert "".join(page.structured_content["data"]["content"] for page in pages) == source
    assert [page.structured_content["data"]["offset"] for page in pages] == [0, 4096, 8192]
    for page in pages:
        assert_bounded(page)
