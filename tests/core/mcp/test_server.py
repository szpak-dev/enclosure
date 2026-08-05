import asyncio
from types import SimpleNamespace
from typing import cast

from mcp.server.context import ServerRequestContext
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams
from modwire_siren import siren_adapter

from enclosure.core.api import api
from enclosure.core.asgi import application
from enclosure.core.mcp.executor import SirenExecutor
from enclosure.core.mcp.server import create_server


def build_server():
    adapter = siren_adapter(
        api.get_openapi_schema(path_prefix="/api"),
        source_path="/api",
        public_path="/siren",
    )
    return create_server(adapter, application, version="test")


def test_registers_only_the_tools_capability() -> None:
    server = build_server()

    capabilities = server.get_capabilities()

    assert server.server_info.name == "enclosure"
    assert server.server_info.version == "test"
    assert capabilities.tools is not None
    assert capabilities.prompts is None
    assert capabilities.resources is None


def test_lists_the_siren_derived_tools() -> None:
    async def list_tools() -> ListToolsResult:
        handler = build_server().get_request_handler("tools/list")
        assert handler is not None
        result = await handler.handler(
            cast(ServerRequestContext[SirenExecutor], None),
            PaginatedRequestParams(),
        )
        assert isinstance(result, ListToolsResult)
        return result

    result = asyncio.run(list_tools())
    tools = {tool.name: tool for tool in result.tools}

    assert "find_languages" in tools
    assert tools["get_language"].input_schema["required"] == ["language_id"]


def test_executes_a_tool_through_the_server_lifespan() -> None:
    async def call_tool() -> CallToolResult:
        server = build_server()
        handler = server.get_request_handler("tools/call")
        assert handler is not None
        async with server.lifespan(server) as executor:
            context = cast(
                ServerRequestContext[SirenExecutor],
                SimpleNamespace(lifespan_context=executor),
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
