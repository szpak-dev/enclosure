import asyncio
from types import SimpleNamespace
from typing import Any, cast

from django.core.wsgi import get_wsgi_application
from mcp.server.context import ServerRequestContext
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams
from sirenity import siren_configuration

from enclosure.core.mcp.server import create_server


def build_server():
    configuration = siren_configuration(
        openapi="enclosure.core.api.api",
        source_path="/api",
        public_path="/siren",
        policy="sirenity.SirenAllowAllPolicy",
        profiles=("sirenity.SirenStructuredFormProfile",),
    )
    return create_server(configuration, get_wsgi_application(), version="test")


def test_registers_only_the_tools_capability() -> None:
    server = build_server()

    capabilities = server.get_capabilities()

    assert server.server_info.name == "enclosure"
    assert server.server_info.version == "test"
    assert capabilities.tools is not None
    assert capabilities.prompts is None
    assert capabilities.resources is None


def test_lists_the_sirenity_catalogue() -> None:
    async def list_tools() -> ListToolsResult:
        handler = build_server().get_request_handler("tools/list")
        assert handler is not None
        result = await handler.handler(
            cast(ServerRequestContext[Any], None),
            PaginatedRequestParams(),
        )
        assert isinstance(result, ListToolsResult)
        return result

    result = asyncio.run(list_tools())
    tools = {tool.name: tool for tool in result.tools}

    assert "find_languages" in tools
    assert "find_project_by_root" in tools
    assert "get_workspace_context" in tools
    assert tools["get_language"].title == "Get a language"
    assert tools["get_language"].input_schema["required"] == ["language_id"]
    assert tools["get_workspace_context"].input_schema["required"] == ["root", "task"]
    assert tools["find_project_by_root"].input_schema["required"] == ["root"]


def test_executes_a_tool_through_the_sirenity_bridge() -> None:
    async def call_tool() -> CallToolResult:
        server = build_server()
        handler = server.get_request_handler("tools/call")
        assert handler is not None
        async with server.lifespan(server) as bridge:
            context = cast(
                ServerRequestContext[Any],
                SimpleNamespace(lifespan_context=bridge),
            )
            result = await handler.handler(
                context,
                CallToolRequestParams(
                    name="get_language",
                    arguments={"language_id": "python"},
                ),
            )
        assert isinstance(result, CallToolResult)
        return result

    result = asyncio.run(call_tool())

    assert result.is_error is False
    assert result.structured_content["properties"]["id"] == "python"
    assert result.content[0].text == result.structured_content["title"]


def test_reports_projected_application_errors() -> None:
    async def call_tool() -> CallToolResult:
        server = build_server()
        handler = server.get_request_handler("tools/call")
        assert handler is not None
        async with server.lifespan(server) as bridge:
            context = cast(
                ServerRequestContext[Any],
                SimpleNamespace(lifespan_context=bridge),
            )
            result = await handler.handler(
                context,
                CallToolRequestParams(
                    name="get_language",
                    arguments={"language_id": "missing-example"},
                ),
            )
        assert isinstance(result, CallToolResult)
        return result

    result = asyncio.run(call_tool())

    assert result.is_error is True
    assert result.structured_content["class"] == ["error"]
    assert result.structured_content["properties"]["status"] == 404


def test_reports_invalid_tool_arguments_without_dispatching() -> None:
    async def call_tool() -> CallToolResult:
        server = build_server()
        handler = server.get_request_handler("tools/call")
        assert handler is not None
        async with server.lifespan(server) as bridge:
            context = cast(
                ServerRequestContext[Any],
                SimpleNamespace(lifespan_context=bridge),
            )
            result = await handler.handler(
                context,
                CallToolRequestParams(name="get_language", arguments={}),
            )
        assert isinstance(result, CallToolResult)
        return result

    result = asyncio.run(call_tool())

    assert result.is_error is True
    assert result.structured_content == {"detail": "Siren MCP invocation is invalid"}
