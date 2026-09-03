import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import httpx2
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, InitializeResult, ListToolsResult
from starlette.types import ASGIApp, Receive, Scope, Send

from enclosure.core.asgi import application, django_application
from enclosure.mcp.application import McpApplication

EXAMPLE_BOUNDARIES_YAML = """boundaries:
  tags:
    - name: example-module
      match: "*"
  flow:
    module_tag: example-module
    layers: []
    analyzers: []
"""
EXAMPLE_HEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: example-project
      match: "*"
      shape:
        max_classes_per_file: 1
"""
EXAMPLE_UNHEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: example-project
      match: "*"
      shape:
        max_classes_per_file: 0
"""


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


class PublicCompositeApplication:
    def __init__(self) -> None:
        self.mcp_application = McpApplication().build()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.mcp_application(scope, receive, send)
        elif scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            await self.mcp_application(scope, receive, send)
        else:
            await django_application(scope, receive, send)


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

    async def workspace_context(
        self,
        root: Path,
        guidance: Mapping[str, Any],
    ) -> tuple[httpx2.Response, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            await self._register_example_project(
                http_client,
                root,
                guidance,
                EXAMPLE_HEALTHY_SHAPE_YAML,
            )
            arguments = {
                "root": str(root),
                "task": "Apply example guidance safely",
            }
            rest_response = await http_client.post(
                "/api/projects/workspace-contexts",
                json=arguments,
            )
            result = await session.call_tool("get_workspace_context", arguments)
            return rest_response, result

    async def incomplete_workspace_context(self, root: Path) -> CallToolResult:
        async with self.session() as (session, http_client):
            await session.initialize()
            await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                EXAMPLE_HEALTHY_SHAPE_YAML,
                bind_guidance=False,
            )
            return await session.call_tool(
                "get_workspace_context",
                {
                    "root": str(root),
                    "task": "Apply example guidance safely",
                },
            )

    async def project_health(
        self,
        root: Path,
        shape_yaml: str,
    ) -> tuple[httpx2.Response, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            project_id = await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                shape_yaml,
            )
            rest_response = await http_client.get(f"/api/projects/{project_id}/health-violations")
            result = await session.call_tool(
                "check_project_health",
                {"project_id": project_id},
            )
            return rest_response, result

    async def _register_example_project(
        self,
        http_client: httpx2.AsyncClient,
        root: Path,
        guidance: Mapping[str, Any],
        shape_yaml: str,
        bind_guidance: bool = True,
    ) -> str:
        category = await http_client.post(
            "/api/records/categories",
            json={
                "title": "Example guidance category",
                "content_schema": {"type": "object"},
            },
        )
        category.raise_for_status()
        tag = await http_client.post(
            "/api/records/tags",
            json={"name": "example-project-guidance"},
        )
        tag.raise_for_status()
        record = await http_client.post(
            "/api/records",
            json={
                "title": "Example operating guidance",
                "content": dict(guidance),
                "category_id": category.json()["id"],
                "tag_ids": [tag.json()["id"]],
                "resources": [],
            },
        )
        record.raise_for_status()
        scaffolding = await http_client.post(
            "/api/scaffoldings",
            json={
                "language_id": "python",
                "name": "Example package",
                "description": "Creates an example package.",
                "spec": {
                    "language": "python",
                    "variables": [],
                    "templates": [
                        {
                            "path": "src/example_package/__init__.py",
                            "content": "",
                            "write_mode": "overwrite",
                        }
                    ],
                },
            },
        )
        scaffolding.raise_for_status()
        discovery = await http_client.post(
            "/api/projects/discoveries",
            json={"root": str(root)},
        )
        discovery.raise_for_status()
        project = await http_client.post(
            "/api/projects",
            json={
                "discovery": discovery.json(),
                "architecture_root": str(root),
                "boundaries_yaml": EXAMPLE_BOUNDARIES_YAML,
                "shape_yaml": shape_yaml,
                "scaffolding_id": scaffolding.json()["id"],
                "record_ids": [record.json()["id"]] if bind_guidance else [],
            },
        )
        project.raise_for_status()
        return project.json()["id"]


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


@pytest.mark.django_db(transaction=True)
def test_reports_workspace_budget_overflow_as_incomplete(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )
    _, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).workspace_context(
            tmp_path,
            {
                "summary": "Example oversized guidance.",
                "guidance": ["Example mandatory directive. " + "x" * 17_000],
            },
        )
    )

    assert result.is_error is True
    assert result.structured_content["status"] == "incomplete"
    assert result.structured_content["reason"] == "presentation_budget_exceeded"
    assert result.structured_content["text_bytes"] > result.structured_content["text_budget"]


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
    assert "create_operating_contract" in tools
    assert "get_project_operating_contract_binding" in tools
    assert tools["get_language"].title == "Get a language"
    assert tools["get_language"].input_schema["required"] == ["language_id"]
    assert tools["get_workspace_context"].input_schema["required"] == ["root", "task"]
    assert tools["find_project_by_root"].input_schema["required"] == ["root"]


@pytest.mark.django_db(transaction=True)
def test_creates_operating_contract_through_public_mcp() -> None:
    result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).call_tool(
            "create_operating_contract",
            {
                "title": "Example operating contract",
                "authority": "example:operating-contract",
                "provenance": "functional-test",
            },
        )
    )

    assert result.is_error is False
    assert result.structured_content["properties"]["title"] == "Example operating contract"
    assert result.structured_content["properties"]["authority"] == "example:operating-contract"


@pytest.mark.django_db(transaction=True)
def test_presents_gating_health_failures_with_targets_and_actions(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )
    rest_response, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).project_health(
            tmp_path,
            EXAMPLE_UNHEALTHY_SHAPE_YAML,
        )
    )

    assert rest_response.json()["healthy"] is False
    assert result.is_error is True
    assert result.structured_content["status"] == "gating-failure"
    assert result.structured_content["failure_count"] > 0
    assert "example_app.py" in " ".join(result.structured_content["targets"])
    assert result.structured_content["next_actions"]
    assert "## Gating failures" in result.content[0].text
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_workspace_bootstrap_before_compact_guidance(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )
    rest_response, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).workspace_context(
            tmp_path,
            {
                "summary": "Example guidance summary.",
                "applies_when": ["Changing example source."],
                "guidance": ["Preserve example behavior."],
                "checks": ["Run the example check."],
            },
        )
    )
    markdown = result.content[0].text
    receipt = result.structured_content

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert markdown.count("# Enclosure") == 1
    assert markdown.index("# Enclosure") < markdown.index("## Project guidance")
    assert markdown.count("Example operating guidance") == 1
    assert markdown.count("Run the example check.") == 1
    assert receipt["project_id"] == rest_response.json()["project_id"]
    assert receipt["root"] == rest_response.json()["root"]
    assert receipt["status"] == "ready"
    assert receipt["guidance_count"] == 1
    assert receipt["check_count"] == 1
    assert "summary" not in receipt["guidance"][0]
    assert "guidance" not in receipt["guidance"][0]
    assert len(markdown.encode("utf-8")) <= 16_384
    assert len(json.dumps(receipt).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_incomplete_workspace_context_as_an_error(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )

    result = asyncio.run(PublicMcpClient(PublicCompositeApplication()).incomplete_workspace_context(tmp_path))

    assert result.is_error is True
    assert result.structured_content["status"] == "incomplete"
    assert result.structured_content["authority"]["kind"] == "project-operating-contract"
    assert result.structured_content["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"
    assert "Readiness: **incomplete**" in result.content[0].text


@pytest.mark.django_db(transaction=True)
def test_presents_healthy_project_health_concisely(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )
    rest_response, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).project_health(
            tmp_path,
            EXAMPLE_HEALTHY_SHAPE_YAML,
        )
    )

    assert rest_response.json()["healthy"] is True
    assert result.is_error is False
    assert result.structured_content["status"] == "healthy"
    assert result.structured_content["failure_count"] == 0
    assert result.structured_content["advisory_count"] == 0
    assert "Status: **healthy**" in result.content[0].text


def test_serves_rest_and_mcp_from_the_composite_application() -> None:
    rest_response, result = asyncio.run(PublicMcpClient(application).call_tool_with_rest())

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert result.structured_content["properties"]["id"] == "python"
    assert result.content[0].text == result.structured_content["title"]
