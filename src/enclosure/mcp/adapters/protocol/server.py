import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar

import structlog
from django.conf import settings
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
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, reset_contextvars

from enclosure.autowiring import application
from enclosure.mcp.services import McpService
from enclosure.mcp.services.diagnostics import McpDiagnosticRequest, McpDiagnostics
from enclosure.mcp.services.operations import ToolCatalogue, ToolInvocation
from enclosure.security.services.actors import ActorExecutionContext

from .authentication import McpActorAuthenticator, McpTokenVerifierAdapter


@dataclass
class McpResponseObservation:
    correlation_id: str = ""
    tool_completed_ns: int = 0
    response_started_ns: int = 0

    def complete_tool(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id
        self.tool_completed_ns = perf_counter_ns()


@dataclass(frozen=True)
class McpResponseSend:
    send: Send
    observation: McpResponseObservation

    async def __call__(self, message: Message) -> None:
        now_ns = perf_counter_ns()
        if message["type"] == "http.response.start" and self.observation.tool_completed_ns:
            self.observation.response_started_ns = now_ns
            structlog.get_logger(__name__).info(
                "mcp_response_serialized",
                correlation_id=self.observation.correlation_id,
                started_ns=self.observation.tool_completed_ns,
                finished_ns=now_ns,
                duration_ns=now_ns - self.observation.tool_completed_ns,
            )
        final_body = (
            message["type"] == "http.response.body"
            and not message.get("more_body", False)
            and self.observation.response_started_ns > 0
        )
        await self.send(message)
        if final_body:
            finished_ns = perf_counter_ns()
            structlog.get_logger(__name__).info(
                "mcp_response_sent",
                correlation_id=self.observation.correlation_id,
                started_ns=self.observation.response_started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - self.observation.response_started_ns,
            )


@dataclass(frozen=True)
class McpResponseDiagnosticsApplication:
    STATE_KEY: ClassVar[str] = "enclosure.mcp.response_observation"

    application: ASGIApp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return
        observation = McpResponseObservation()
        scope.setdefault("state", {})[self.STATE_KEY] = observation
        await self.application(scope, receive, McpResponseSend(send=send, observation=observation))

    @classmethod
    def observation(cls, scope: Scope) -> McpResponseObservation:
        return scope["state"][cls.STATE_KEY]


@dataclass(frozen=True)
class McpProtocolRuntime:
    service: McpService
    catalogue: ToolCatalogue
    actors: ActorExecutionContext


@dataclass(frozen=True)
class McpProtocolServer:
    SESSION_MODE: ClassVar[str] = "stateless-http"

    release: str
    actor_authenticator: McpActorAuthenticator
    token_verifier: McpTokenVerifierAdapter

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
        if settings.SECURITY_MCP_AUTH_REQUIRED:
            protocol_application = server.streamable_http_app(
                streamable_http_path="/mcp",
                json_response=True,
                stateless_http=True,
                auth=self.actor_authenticator.settings(),
                token_verifier=self.token_verifier,
            )
        else:
            protocol_application = server.streamable_http_app(
                streamable_http_path="/mcp",
                json_response=True,
                stateless_http=True,
            )
        return McpResponseDiagnosticsApplication(protocol_application)

    @asynccontextmanager
    async def _lifespan(
        self,
        server: Server[McpProtocolRuntime],
    ) -> AsyncIterator[McpProtocolRuntime]:
        started_ns = perf_counter_ns()
        container = application.create_container()
        try:
            service = container.get(McpService)
            server.instructions = service.instructions()
            finished_ns = perf_counter_ns()
            structlog.get_logger(__name__).info(
                "mcp_runtime_started",
                release=self.release,
                process_id=os.getpid(),
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                session_mode=self.SESSION_MODE,
                session_reused=False,
            )
            yield McpProtocolRuntime(
                service=service,
                catalogue=service.catalogue(),
                actors=container.get(ActorExecutionContext),
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
        process_id = os.getpid()
        correlation_id = f"{self.release}:{process_id}:{context.request_id}"
        request = McpDiagnosticRequest(
            correlation_id=correlation_id,
            release=self.release,
            process_id=process_id,
            cache_directory=settings.MODWIRE_CACHE_DIRECTORY,
            session_mode=self.SESSION_MODE,
            session_reused=False,
        )
        context_tokens = bind_contextvars(correlation_id=correlation_id)
        actor_token = context.lifespan_context.actors.bind(self.actor_authenticator.authenticate())
        try:
            result = await asyncio.to_thread(
                context.lifespan_context.service.invoke,
                ToolInvocation(
                    operation_id=params.name,
                    arguments=params.arguments,
                ),
                request,
            )
            response = CallToolResult(
                content=[TextContent(type="text", text=result.presentation.markdown)],
                structured_content=result.presentation.structured_content.model_dump(mode="json"),
                is_error=result.presentation.is_error(),
                _meta={
                    McpDiagnostics.META_KEY: result.diagnostics.model_dump(mode="json"),
                },
            )
            McpResponseDiagnosticsApplication.observation(context.request.scope).complete_tool(correlation_id)
            return response
        finally:
            context.lifespan_context.actors.reset(actor_token)
            reset_contextvars(**context_tokens)
