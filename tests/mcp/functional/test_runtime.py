import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, cast

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, InitializeResult, ListToolsResult
from starlette.types import ASGIApp, Scope

from enclosure.core.asgi import application
from enclosure.mcp.application import McpApplication


class ApplicationLifespan:
    def __init__(self, application: ASGIApp) -> None:
        self.application = application

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        outgoing: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        task = asyncio.create_task(
            self.application(
                cast(
                    Scope,
                    {
                        "type": "lifespan",
                        "asgi": {"version": "3.0", "spec_version": "2.0"},
                        "state": {},
                    },
                ),
                incoming.get,
                outgoing.put,
            )
        )
        await incoming.put({"type": "lifespan.startup"})
        startup = await asyncio.wait_for(outgoing.get(), timeout=5)
        if startup["type"] != "lifespan.startup.complete":
            await task
            raise RuntimeError(f"ASGI startup failed: {startup}")
        try:
            yield
        finally:
            await incoming.put({"type": "lifespan.shutdown"})
            shutdown = await asyncio.wait_for(outgoing.get(), timeout=5)
            if shutdown["type"] != "lifespan.shutdown.complete":
                raise RuntimeError(f"ASGI shutdown failed: {shutdown}")
            await asyncio.wait_for(task, timeout=5)


class PublicMcpClient:
    def __init__(self, application: ASGIApp) -> None:
        self.application = application

    @asynccontextmanager
    async def session(self) -> AsyncIterator[tuple[ClientSession, httpx2.AsyncClient]]:
        async with (
            ApplicationLifespan(self.application).run(),
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=self.application),
                base_url="http://localhost:8000",
            ) as http_client,
            streamable_http_client(
                "http://localhost:8000/mcp",
                http_client=http_client,
                terminate_on_close=False,
            ) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            yield session, http_client

    async def initialize(self) -> InitializeResult:
        async with self.session() as (session, _):
            return await session.initialize()

    async def list_tools(self) -> ListToolsResult:
        async with self.session() as (session, _):
            await session.initialize()
            return await session.list_tools()

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> CallToolResult:
        async with self.session() as (session, _):
            await session.initialize()
            return await session.call_tool(name, arguments)

    async def call_tool_with_rest(self) -> tuple[httpx2.Response, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            rest_response = await http_client.get("/api/languages")
            result = await session.call_tool(
                "get_language",
                {"language_id": "python"},
            )
            return rest_response, result


def test_reports_invalid_tool_arguments() -> None:
    result = asyncio.run(PublicMcpClient(McpApplication().build()).call_tool("get_language", {}))

    assert result.is_error is True
    assert result.structured_content == {"detail": "Siren MCP invocation is invalid"}
    assert result.content[0].text == "Siren MCP invocation is invalid"


def test_reports_projected_application_errors() -> None:
    result = asyncio.run(
        PublicMcpClient(McpApplication().build()).call_tool(
            "get_language",
            {"language_id": "missing-example"},
        )
    )

    assert result.is_error is True
    assert result.structured_content["class"] == ["error"]
    assert result.structured_content["properties"]["status"] == 404


def test_initializes_with_the_stable_server_contract() -> None:
    initialization = asyncio.run(PublicMcpClient(McpApplication().build()).initialize())

    assert initialization.server_info.name == "enclosure"
    assert initialization.server_info.title == "Enclosure"
    assert initialization.capabilities.tools is not None
    assert initialization.capabilities.prompts is None
    assert initialization.capabilities.resources is None
    assert initialization.instructions == (
        "Enclosure provides project operating context and architecture checks. "
        "Call get_workspace_context before working in a registered workspace."
    )


def test_lists_the_siren_catalogue() -> None:
    result = asyncio.run(PublicMcpClient(McpApplication().build()).list_tools())
    tools = {tool.name: tool for tool in result.tools}

    assert "find_languages" in tools
    assert "find_project_by_root" in tools
    assert "get_workspace_context" in tools
    assert tools["get_language"].title == "Get a language"
    assert tools["get_language"].input_schema["required"] == ["language_id"]
    assert tools["get_workspace_context"].input_schema["required"] == ["root", "task"]
    assert tools["find_project_by_root"].input_schema["required"] == ["root"]


def test_serves_rest_and_mcp_from_the_composite_application() -> None:
    rest_response, result = asyncio.run(PublicMcpClient(application).call_tool_with_rest())

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert result.structured_content["properties"]["id"] == "python"
    assert result.content[0].text == result.structured_content["title"]
