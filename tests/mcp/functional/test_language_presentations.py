import asyncio
import json

from mcp.types import CallToolResult

from .test_runtime import PublicCompositeApplication, PublicMcpClient


async def language_presentations() -> dict[str, CallToolResult]:
    client = PublicMcpClient(PublicCompositeApplication())
    async with client.session() as (session, _):
        await session.initialize()
        return {
            "find_languages": await session.call_tool("find_languages", {}),
            "get_language": await session.call_tool("get_language", {"language_id": "python"}),
        }


def test_presents_language_catalogue_and_detail_through_public_mcp() -> None:
    results = asyncio.run(language_presentations())

    for operation, result in results.items():
        assert result.is_error is False, operation
        assert result.structured_content["operation_id"] == operation
        assert result.structured_content["status"] == "ok"
        assert result.structured_content["data"].get("reason") != "presentation_incomplete"
        assert len(result.content[0].text.encode("utf-8")) <= 16_384
        assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192

    catalogue = results["find_languages"].structured_content
    items = catalogue["data"]["items"]
    assert catalogue["data"]["count"] == 6
    assert [item["id"] for item in items] == [
        "markdown",
        "mermaid",
        "php",
        "python",
        "typescript",
        "yaml",
    ]
    assert all(set(item) == {"id", "name", "aliases", "source_extensions"} for item in items)
    assert catalogue["follow_ups"] == [
        {"operation_id": "get_language", "arguments": {"language_id": item["id"]}} for item in items
    ]
    assert "| ID | Name | Aliases | Source extensions |" in results["find_languages"].content[0].text

    detail = results["get_language"].structured_content
    assert detail["data"] == {
        "id": "python",
        "name": "Python",
        "aliases": ["py"],
        "source_extensions": [".py"],
    }
    assert detail["follow_ups"] == []
    detail_markdown = results["get_language"].content[0].text
    assert "Bounded operation receipt" not in detail_markdown
    assert "Available actions" not in detail_markdown
    assert "## Links" not in detail_markdown
