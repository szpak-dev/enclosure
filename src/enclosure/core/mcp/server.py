from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.types import CallToolRequestParams, CallToolResult, ListToolsResult, PaginatedRequestParams
from modwire_siren import SirenAdapter
from starlette.types import ASGIApp

from .executor import SirenExecutor
from .toolset import SirenToolset


def create_server(
    adapter: SirenAdapter,
    application: ASGIApp,
    *,
    version: str,
) -> Server[SirenExecutor]:
    tools = SirenToolset(adapter).tools()

    @asynccontextmanager
    async def lifespan(_: Server[SirenExecutor]) -> AsyncIterator[SirenExecutor]:
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            yield SirenExecutor(adapter, client)

    async def list_tools(
        _: ServerRequestContext[SirenExecutor],
        __: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    async def call_tool(
        context: ServerRequestContext[SirenExecutor],
        params: CallToolRequestParams,
    ) -> CallToolResult:
        return await context.lifespan_context.execute(
            params.name,
            params.arguments or {},
        )

    return Server(
        "enclosure",
        version=version,
        title="Enclosure",
        description="Siren-derived tools for the Enclosure runtime.",
        instructions="Use the available tools to inspect and operate Enclosure resources.",
        lifespan=lifespan,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
