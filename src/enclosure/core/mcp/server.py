import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import Client, WSGITransport
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)
from sirenity import SirenConfiguration, SirenMcpInvocation, siren_mcp

from .executor import SirenExecutor


def create_server(
    configuration: SirenConfiguration,
    application: Any,
    *,
    version: str,
) -> Server[Any]:
    tools = [
        Tool(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            input_schema=dict(tool.input_schema),
        )
        for tool in configuration.catalogue().snapshot()
    ]

    @asynccontextmanager
    async def lifespan(_: Server[Any]) -> AsyncIterator[Any]:
        with Client(
            transport=WSGITransport(app=application),
            base_url="http://localhost",
        ) as client:
            yield siren_mcp(
                configuration,
                executor=SirenExecutor(configuration.adapter(), client),
            )

    async def list_tools(
        _: ServerRequestContext[Any],
        __: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    async def call_tool(
        context: ServerRequestContext[Any],
        params: CallToolRequestParams,
    ) -> CallToolResult:
        result = await asyncio.to_thread(
            context.lifespan_context.invoke,
            SirenMcpInvocation(
                operation_id=params.name,
                arguments=params.arguments or {},
            ),
        )
        document = dict(result.structured_content)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(document))],
            structured_content=document,
            is_error=result.is_error,
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
