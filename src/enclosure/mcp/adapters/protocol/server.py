import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

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
from starlette.types import ASGIApp

from enclosure.autowiring import application
from enclosure.mcp.services import McpService
from enclosure.mcp.services.operations import ToolCatalogue, ToolInvocation


@dataclass(frozen=True)
class McpProtocolRuntime:
    service: McpService
    catalogue: ToolCatalogue


@dataclass(frozen=True)
class McpProtocolServer:
    release: str

    def build(self) -> ASGIApp:
        server = Server(
            "enclosure",
            version=self.release,
            title="Enclosure",
            description="Siren-derived tools for the Enclosure runtime.",
            lifespan=self._lifespan,
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )
        return server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
        )

    @asynccontextmanager
    async def _lifespan(
        self,
        server: Server[McpProtocolRuntime],
    ) -> AsyncIterator[McpProtocolRuntime]:
        container = application.create_container()
        try:
            service = container.get(McpService)
            if not isinstance(service, McpService):
                raise RuntimeError("The MCP service graph is incomplete.")
            server.instructions = service.instructions()
            yield McpProtocolRuntime(
                service=service,
                catalogue=service.catalogue(),
            )
        finally:
            container.close()

    async def _list_tools(
        self,
        context: ServerRequestContext[McpProtocolRuntime],
        params: PaginatedRequestParams,
    ) -> ListToolsResult:
        return ListToolsResult(
            tools=[
                Tool(
                    name=tool.name,
                    title=tool.title,
                    description=tool.description,
                    input_schema=dict(tool.input_schema),
                )
                for tool in context.lifespan_context.catalogue.tools
            ]
        )

    async def _call_tool(
        self,
        context: ServerRequestContext[McpProtocolRuntime],
        params: CallToolRequestParams,
    ) -> CallToolResult:
        result = await asyncio.to_thread(
            context.lifespan_context.service.invoke,
            ToolInvocation(
                operation_id=params.name,
                arguments=params.arguments or {},
            ),
        )
        return CallToolResult(
            content=[TextContent(type="text", text=result.markdown)],
            structured_content=result.structured_content.model_dump(mode="json"),
            is_error=result.is_error(),
        )
