import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import httpx2
import pytest
from django.test import Client
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

    async def collection_pages(
        self,
        operations: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, tuple[CallToolResult, CallToolResult, CallToolResult]]:
        async with self.session() as (session, _):
            await session.initialize()
            results = {}
            for operation, identity in operations.items():
                first = await session.call_tool(
                    operation,
                    {**identity, "offset": 0, "limit": 1},
                )
                follow_ups = first.structured_content["follow_ups"]
                final = (
                    await session.call_tool(
                        operation,
                        follow_ups[0]["arguments"],
                    )
                    if follow_ups
                    else first
                )
                empty = await session.call_tool(
                    operation,
                    {
                        **identity,
                        "offset": final.structured_content["data"]["next_offset"],
                        "limit": final.structured_content["data"]["limit"],
                    },
                )
                results[operation] = (first, final, empty)
            return results

    async def diagram_presentations(self) -> dict[str, CallToolResult]:
        async with self.session() as (session, _):
            await session.initialize()
            results = {}

            async def call(name: str, arguments: Mapping[str, Any]) -> CallToolResult:
                result = await session.call_tool(name, arguments)
                results[name] = result
                return result

            await call("find_diagram_kinds", {})
            await call("get_diagram_kind", {"kind": "flowchart"})
            await call("get_diagram_command_schema", {"kind": "flowchart", "operation": "update_element"})
            created_set = await call(
                "create_diagram_set",
                {"title": "MCP diagrams", "description": "Diagram presentation verification."},
            )
            diagram_set_id = created_set.structured_content["data"]["id"]
            await call("find_diagram_sets", {})
            await call("get_diagram_set", {"diagram_set_id": diagram_set_id})
            await call(
                "update_diagram_set",
                {"diagram_set_id": diagram_set_id, "title": "Updated MCP diagrams"},
            )
            created_diagram = await call(
                "create_diagram",
                {"diagram_set_id": diagram_set_id, "title": "MCP flow", "kind": "flowchart"},
            )
            diagram_id = created_diagram.structured_content["data"]["id"]
            await call("find_diagram_set_diagrams", {"diagram_set_id": diagram_set_id})
            await call(
                "get_diagram_set_diagram",
                {"diagram_set_id": diagram_set_id, "diagram_id": diagram_id},
            )
            await call("find_diagrams", {})
            await call("get_diagram", {"diagram_id": diagram_id})
            applied = await call(
                "apply_diagram_command",
                {
                    "diagram_id": diagram_id,
                    "expected_revision": 1,
                    "operation": "add_start",
                    "arguments": {"id": "start", "label": "Start"},
                },
            )
            batched = await call(
                "apply_diagram_command_batch",
                {
                    "diagram_id": diagram_id,
                    "expected_revision": applied.structured_content["data"]["revision"],
                    "commands": [
                        {"operation": "add_end", "arguments": {"id": "end", "label": "End"}},
                        {
                            "operation": "add_flow",
                            "arguments": {"id": "flow", "source_id": "start", "target_id": "end"},
                        },
                    ],
                },
            )
            await call(
                "create_diagram_batch",
                {
                    "diagram_set_id": diagram_set_id,
                    "title": "MCP batch-created flow",
                    "kind": "flowchart",
                    "commands": [
                        {"operation": "add_start", "arguments": {"id": "start", "label": "Start"}},
                        {"operation": "add_end", "arguments": {"id": "end", "label": "End"}},
                    ],
                },
            )
            updated = await call(
                "update_diagram",
                {
                    "diagram_id": diagram_id,
                    "expected_revision": batched.structured_content["data"]["revision"],
                    "title": "Updated MCP flow",
                },
            )
            await call(
                "read_diagram_content",
                {
                    "diagram_id": diagram_id,
                    "document": "snapshot",
                    "expected_revision": updated.structured_content["data"]["revision"],
                    "offset": 0,
                    "limit": 32,
                },
            )
            await call("delete_diagram", {"diagram_id": diagram_id})
            await call("delete_diagram_set", {"diagram_set_id": diagram_set_id})
            return results

    async def record_presentations(self) -> dict[str, CallToolResult]:
        async with self.session() as (session, _):
            await session.initialize()
            results = {}

            async def call(name: str, arguments: Mapping[str, Any]) -> CallToolResult:
                result = await session.call_tool(name, arguments)
                results[name] = result
                return result

            tag = await call("create_record_tag", {"name": "MCP primary tag"})
            tag_id = tag.structured_content["data"]["id"]
            await call("get_record_tag", {"tag_id": tag_id})
            await call("update_record_tag", {"tag_id": tag_id, "name": "MCP updated tag"})
            await call("create_record_tag", {"name": "MCP page tag"})
            disposable_tag = await call("create_record_tag", {"name": "MCP disposable tag"})
            await call("find_record_tags", {"offset": 0, "limit": 1})

            category = await call(
                "create_record_category",
                {
                    "title": "MCP primary category",
                    "content_schema": {
                        "type": "object",
                        "properties": {"headline": {"type": "string"}},
                        "required": ["headline"],
                    },
                },
            )
            category_id = category.structured_content["data"]["id"]
            await call("get_record_category", {"category_id": category_id})
            await call(
                "update_record_category",
                {"category_id": category_id, "title": "MCP updated category"},
            )
            schema = await call(
                "update_record_category_content_schema",
                {
                    "category_id": category_id,
                    "content_schema": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "summary": {"type": "string"},
                        },
                        "required": ["headline"],
                    },
                },
            )
            schema_data = schema.structured_content["data"]
            await call(
                "read_record_category_content_schema",
                {
                    "category_id": category_id,
                    "schema_version": schema_data["version"],
                    "expected_revision": schema_data["revision"],
                    "offset": 0,
                    "limit": 64,
                },
            )
            await call(
                "create_record_category",
                {"title": "MCP page category", "content_schema": {"type": "object"}},
            )
            disposable_category = await call(
                "create_record_category",
                {"title": "MCP disposable category", "content_schema": {"type": "object"}},
            )
            await call("find_record_categories", {"offset": 0, "limit": 1})

            source = "record_source = 'bounded MCP content'\n" * 24
            record = await call(
                "create_record",
                {
                    "title": "MCP primary record",
                    "content": {"headline": "Primary"},
                    "category_id": category_id,
                    "tag_ids": [tag_id],
                    "resources": [
                        {
                            "path": "guidance/record.py",
                            "language": "python",
                            "content": source,
                        }
                    ],
                },
            )
            record_id = record.structured_content["data"]["id"]
            secondary_record = await session.call_tool(
                "create_record",
                {
                    "title": "MCP secondary record",
                    "content": {"headline": "Secondary"},
                    "category_id": category_id,
                    "tag_ids": [tag_id],
                    "resources": [],
                },
            )
            secondary_record_id = secondary_record.structured_content["data"]["id"]
            await call("find_records", {"offset": 0, "limit": 1})
            await call("search_records", {"query": "primary record", "limit": 2})
            await call("get_record", {"record_id": record_id})
            updated_record = await call(
                "update_record",
                {
                    "record_id": record_id,
                    "title": "MCP revised record",
                    "content": {"headline": "Revised", "summary": "Verified"},
                    "category_id": category_id,
                    "tag_ids": [tag_id],
                    "resources": [
                        {
                            "path": "guidance/record.py",
                            "language": "python",
                            "content": source,
                        }
                    ],
                },
            )
            manifest = updated_record.structured_content["data"]["resources"][0]
            await call(
                "read_record_resource",
                {
                    "record_id": record_id,
                    "path": manifest["path"],
                    "expected_revision": manifest["revision"],
                    "offset": 0,
                    "limit": 64,
                },
            )
            await call("delete_record", {"record_id": secondary_record_id})
            await call(
                "delete_record_category",
                {"category_id": disposable_category.structured_content["data"]["id"]},
            )
            await call(
                "delete_record_tag",
                {"tag_id": disposable_tag.structured_content["data"]["id"]},
            )
            return results

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
            project_id, workspace_id = await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                shape_yaml,
            )
            rest_response = await http_client.get(
                f"/api/projects/{project_id}/workspaces/{workspace_id}/health-violations"
            )
            result = await session.call_tool(
                "check_project_health",
                {"project_id": project_id, "workspace_id": workspace_id},
            )
            return rest_response, result

    async def oversized_guidance_health(self, root: Path) -> tuple[httpx2.Response, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            project_id, workspace_id = await self._register_example_project(
                http_client,
                root,
                {"guidance": ["x" * 9000]},
                EXAMPLE_HEALTHY_SHAPE_YAML,
            )
            rest_response = await http_client.get(
                f"/api/projects/{project_id}/workspaces/{workspace_id}/health-violations"
            )
            result = await session.call_tool(
                "check_project_health",
                {"project_id": project_id, "workspace_id": workspace_id},
            )
            return rest_response, result

    async def project_insights(self, root: Path) -> tuple[CallToolResult, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            project_id, workspace_id = await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                EXAMPLE_HEALTHY_SHAPE_YAML,
            )
            overview = await session.call_tool(
                "read_project_insights",
                {"project_id": project_id, "workspace_id": workspace_id},
            )
            section = overview.structured_content["data"]["sections"][0]
            page = await session.call_tool(
                "read_project_insight_page",
                {
                    "project_id": project_id,
                    "workspace_id": workspace_id,
                    "path": section["path"],
                    "expected_revision": overview.structured_content["data"]["revision"],
                    "offset": 0,
                    "limit": 1,
                },
            )
            return overview, page

    async def project_configuration_content(self, root: Path) -> tuple[CallToolResult, CallToolResult]:
        async with self.session() as (session, http_client):
            await session.initialize()
            project_id, _ = await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                EXAMPLE_HEALTHY_SHAPE_YAML,
            )
            configurations = await session.call_tool(
                "find_project_architecture_configurations",
                {"project_id": project_id},
            )
            reference = configurations.structured_content["data"]["items"][0]
            configuration = await session.call_tool(
                "get_project_architecture_configuration",
                {"project_id": project_id, "configuration_id": reference["id"]},
            )
            content = await session.call_tool(
                "read_project_architecture_configuration_content",
                {
                    "project_id": project_id,
                    "configuration_id": reference["id"],
                    "document": "boundaries_yaml",
                    "expected_revision": reference["revision"],
                    "offset": 0,
                    "limit": 12,
                },
            )
            return configuration, content

    async def workspace_rebinding(
        self,
        root: Path,
        worktree: Path,
        relocated: Path,
    ) -> tuple[CallToolResult, CallToolResult, CallToolResult, CallToolResult, httpx2.Response]:
        async with self.session() as (session, http_client):
            await session.initialize()
            project_id, _ = await self._register_example_project(
                http_client,
                root,
                {"summary": "Example project guidance."},
                EXAMPLE_HEALTHY_SHAPE_YAML,
            )
            bound = await session.call_tool(
                "bind_workspace",
                {
                    "project_id": project_id,
                    "root": str(worktree),
                    "architecture_root": str(worktree),
                },
            )
            workspace_id = bound.structured_content["data"]["id"]
            worktree.rename(relocated)
            stale = await session.call_tool(
                "inspect_workspace",
                {"project_id": project_id, "workspace_id": workspace_id},
            )
            replaced = await session.call_tool(
                "replace_workspace",
                {
                    "project_id": project_id,
                    "workspace_id": workspace_id,
                    "root": str(relocated),
                    "architecture_root": str(relocated),
                    "expected_revision": 1,
                },
            )
            resolved = await session.call_tool("resolve_workspace", {"root": str(relocated)})
            rest_resolution = await http_client.post(
                "/api/projects/workspace-resolutions",
                json={"root": str(relocated)},
            )
            return bound, stale, replaced, resolved, rest_resolution

    async def _register_example_project(
        self,
        http_client: httpx2.AsyncClient,
        root: Path,
        guidance: Mapping[str, Any],
        shape_yaml: str,
        bind_guidance: bool = True,
    ) -> tuple[str, str]:
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
        resolution = project.json()
        return resolution["project"]["id"], resolution["workspace"]["id"]


def test_reports_invalid_tool_arguments() -> None:
    result = asyncio.run(PublicMcpClient(McpApplication().build()).call_tool("get_language", {}))

    assert result.is_error is True
    assert result.structured_content == {
        "operation_id": "get_language",
        "status": "error",
        "summary": "Siren MCP invocation is invalid",
        "data": {"classes": [], "reason": "operation_failed"},
        "follow_ups": [],
    }
    assert "Siren MCP invocation is invalid" in result.content[0].text


def test_bounds_an_oversized_unknown_operation() -> None:
    result = asyncio.run(PublicMcpClient(McpApplication().build()).call_tool("unknown-" + "x" * 10_000, {}))

    assert result.is_error is True
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["reason"] == "presentation_budget_exceeded"
    assert len(result.structured_content["operation_id"].encode("utf-8")) <= 256
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


def test_reports_projected_application_errors() -> None:
    result = asyncio.run(
        PublicMcpClient(McpApplication().build()).call_tool(
            "get_language",
            {"language_id": "missing-example"},
        )
    )

    assert result.is_error is True
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["classes"] == ["error"]
    assert result.structured_content["data"]["status"] == 404


@pytest.mark.django_db(transaction=True)
def test_bounds_oversized_workspace_guidance_before_rendering(tmp_path: Path) -> None:
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
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["readiness"] == "incomplete"
    projected_guidance = result.structured_content["data"]["guidance"][0]["guidance"][0]
    assert isinstance(projected_guidance, str)
    assert projected_guidance.startswith("Example mandatory directive.")
    assert projected_guidance.endswith("...")
    assert len(projected_guidance) == 512
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


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
    assert "resolve_workspace" in tools
    assert "bind_workspace" in tools
    assert "replace_workspace" in tools
    assert "inspect_workspace" in tools
    assert "get_workspace_context" in tools
    assert "create_operating_contract" in tools
    assert "get_project_operating_contract_binding" in tools
    assert "read_project_architecture_configuration_content" in tools
    assert "read_project_insight_page" in tools
    assert tools["get_language"].title == "Get a language"
    assert tools["get_language"].input_schema["required"] == ["language_id"]
    assert tools["get_workspace_context"].input_schema["required"] == ["root", "task"]
    assert tools["find_project_by_root"].input_schema["required"] == ["root"]
    assert tools["check_project_health"].input_schema["required"] == ["project_id", "workspace_id"]
    batch_commands = tools["apply_diagram_command_batch"].input_schema["properties"]["commands"]
    assert batch_commands["minItems"] == 1
    assert batch_commands["maxItems"] == 1000
    creation_commands = tools["create_diagram_batch"].input_schema["properties"]["commands"]
    assert creation_commands["minItems"] == 1
    assert creation_commands["maxItems"] == 1000


def test_presents_the_api_root_without_embedded_operation_schemas() -> None:
    result = asyncio.run(PublicMcpClient(McpApplication().build()).call_tool("get_api_root", {}))

    assert result.is_error is False
    assert result.structured_content["operation_id"] == "get_api_root"
    assert result.structured_content["status"] == "ok"
    assert result.structured_content["data"]["title"] == "Enclosure API"
    assert result.structured_content["data"]["entry_points"]
    assert "actions" not in result.structured_content["data"]
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_rebinds_a_workspace_through_public_mcp(tmp_path: Path) -> None:
    root = tmp_path / "main"
    worktree = tmp_path / "feature"
    relocated = tmp_path / "relocated-feature"
    root.mkdir()
    worktree.mkdir()
    (root / "uv.lock").write_text("", encoding="utf-8")
    (root / "example_app.py").write_text("class ExampleApplication:\n    pass\n", encoding="utf-8")

    bound, stale, replaced, resolved, rest_resolution = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).workspace_rebinding(root, worktree, relocated)
    )

    assert bound.is_error is False
    assert bound.structured_content["status"] == "ok"
    assert stale.is_error is False
    assert stale.structured_content["data"]["state"] == "missing_root"
    assert replaced.is_error is False
    assert replaced.structured_content["data"]["revision"] == 2
    assert replaced.structured_content["data"]["root"] == str(relocated)
    assert resolved.is_error is False
    assert resolved.structured_content["status"] == "ok"
    assert rest_resolution.status_code == 200
    assert rest_resolution.json()["workspace"]["revision"] == 2
    assert rest_resolution.json()["workspace"]["root"] == str(relocated)
    assert rest_resolution.json()["project"]["title"] == "main"


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
    assert result.structured_content["status"] == "ok"
    assert result.structured_content["data"]["title"] == "Example operating contract"
    assert result.structured_content["data"]["authority"] == "example:operating-contract"


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
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["outcome"] == "gating-failure"
    assert result.structured_content["data"]["failure_count"] > 0
    assert "example_app.py" in " ".join(result.structured_content["data"]["targets"])
    assert result.structured_content["data"]["next_actions"]
    assert "## Gating failures" in result.content[0].text
    assert len(result.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_guidance_health_rules_through_public_mcp(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )

    rest_response, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).oversized_guidance_health(tmp_path)
    )

    assert rest_response.json()["failures"][0]["rule"] == "guidance-oversized"
    assert result.is_error is True
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["outcome"] == "gating-failure"
    assert result.structured_content["data"]["failure_count"] == 1
    assert result.structured_content["data"]["next_actions"][0].endswith("against guidance-oversized.")
    assert "**guidance-oversized**" in result.content[0].text


@pytest.mark.django_db(transaction=True)
def test_presents_workspace_bootstrap_before_compact_guidance(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )
    directives = [f"Preserve example behavior {index}." for index in range(26)]
    rest_response, result = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).workspace_context(
            tmp_path,
            {
                "summary": "Example guidance summary.",
                "applies_when": ["Changing example source."],
                "guidance": directives,
                "checks": ["Run the example check."],
            },
        )
    )
    markdown = result.content[0].text
    envelope = result.structured_content
    data = envelope["data"]
    receipt = data["receipt"]

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert envelope["status"] == "ok"
    assert markdown.count("# Enclosure") == 1
    assert markdown.index("# Enclosure") < markdown.index("## Selected guidance")
    assert markdown.count("Example operating guidance") == 1
    assert markdown.count("Run the example check.") == 1
    assert data["project_id"] == rest_response.json()["project_id"]
    assert data["root"] == rest_response.json()["root"]
    assert data["readiness"] == "ready"
    assert receipt["authority"] == rest_response.json()["receipt"]["authority"]
    assert receipt["items"][0] == rest_response.json()["receipt"]["items"][0]
    assert data["guidance"][0]["guidance"] == directives
    assert directives[-1] in markdown
    assert envelope["follow_ups"] == []
    assert receipt["required_checks"] == ["Run the example check."]
    assert receipt["coverage"] == {
        "status": "complete",
        "selected_count": 1,
        "omitted_count": 0,
        "diagnostic_count": 0,
    }
    assert receipt["stop_condition"] == "selected-guidance-and-checks"
    assert "summary" not in receipt["items"][0]
    assert "guidance" not in receipt["items"][0]
    assert len(markdown.encode("utf-8")) <= 16_384
    assert len(json.dumps(data).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_incomplete_workspace_context_as_an_error(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )

    result = asyncio.run(PublicMcpClient(PublicCompositeApplication()).incomplete_workspace_context(tmp_path))

    assert result.is_error is True
    assert result.structured_content["status"] == "error"
    assert result.structured_content["data"]["readiness"] == "incomplete"
    receipt = result.structured_content["data"]["receipt"]
    assert receipt["authority"]["kind"] == "project-operating-contract"
    assert receipt["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"
    assert receipt["coverage"]["status"] == "partial"
    assert receipt["stop_condition"] == "resolve-context-gaps"
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
    assert result.structured_content["status"] == "ok"
    assert result.structured_content["data"]["outcome"] == "healthy"
    assert result.structured_content["data"]["failure_count"] == 0
    assert result.structured_content["data"]["advisory_count"] == 0
    assert "Status: **healthy**" in result.content[0].text


@pytest.mark.django_db(transaction=True)
def test_presents_complete_project_insights_with_bounded_pages_available(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )

    overview, page = asyncio.run(PublicMcpClient(PublicCompositeApplication()).project_insights(tmp_path))
    data = overview.structured_content["data"]

    assert overview.is_error is False
    assert overview.structured_content["status"] == "ok"
    assert data["reports"]
    assert data["sections"]
    assert all("metadata" in report for report in data["reports"])
    assert all(set(section) == {"path", "total"} for section in data["sections"])
    assert page.is_error is False
    assert page.structured_content["data"]["revision"] == data["revision"]
    assert page.structured_content["data"]["path"] == data["sections"][0]["path"]
    assert len(page.structured_content["data"]["items"]) == 1
    assert len(overview.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(overview.structured_content).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_bounded_configuration_content_from_a_siren_action(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_app.py").write_text(
        "class ExampleApplication:\n    pass\n",
        encoding="utf-8",
    )

    configuration, content = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).project_configuration_content(tmp_path)
    )

    actions = {action["name"] for action in configuration.structured_content["data"]["actions"]}
    assert "read_project_architecture_configuration_content" in actions
    assert content.is_error is False
    assert content.structured_content["status"] == "ok"
    assert content.structured_content["data"]["content"] == EXAMPLE_BOUNDARIES_YAML[:12]
    assert content.structured_content["data"]["next_offset"] == 12
    assert len(content.content[0].text.encode("utf-8")) <= 16_384
    assert len(json.dumps(content.structured_content).encode("utf-8")) <= 8_192


@pytest.mark.django_db(transaction=True)
def test_presents_every_diagram_operation_from_siren_documents() -> None:
    results = asyncio.run(PublicMcpClient(PublicCompositeApplication()).diagram_presentations())

    assert set(results) == {
        "apply_diagram_command",
        "apply_diagram_command_batch",
        "create_diagram",
        "create_diagram_batch",
        "create_diagram_set",
        "delete_diagram",
        "delete_diagram_set",
        "find_diagram_kinds",
        "find_diagram_set_diagrams",
        "find_diagram_sets",
        "find_diagrams",
        "get_diagram",
        "get_diagram_command_schema",
        "get_diagram_kind",
        "get_diagram_set",
        "get_diagram_set_diagram",
        "read_diagram_content",
        "update_diagram",
        "update_diagram_set",
    }
    for operation, result in results.items():
        assert result.is_error is False, operation
        assert result.structured_content["status"] == "ok", operation
        assert result.structured_content["data"].get("reason") != "presentation_incomplete", operation
        assert len(result.content[0].text.encode("utf-8")) <= 16_384, operation
        assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192, operation

    kinds = results["find_diagram_kinds"].structured_content["data"]
    assert kinds["count"] > 1
    assert all({"id", "name", "href"} <= item.keys() for item in kinds["items"])

    diagram_kind = results["get_diagram_kind"].structured_content["data"]
    assert diagram_kind["id"] == "flowchart"
    assert "add_start" in diagram_kind["commands"]["keys"]

    command = results["get_diagram_command_schema"].structured_content["data"]
    assert command["kind"] == "flowchart"
    assert command["operation"] == "update_element"
    assert command["arguments_schema"]["oneOf"]

    references = results["find_diagrams"].structured_content["data"]["items"]
    assert len(references) == 1
    assert set(references[0]) == {"href", "id", "kind", "revision", "title"}

    applied = results["apply_diagram_command"].structured_content["data"]
    batched = results["apply_diagram_command_batch"].structured_content["data"]
    created_batch = results["create_diagram_batch"].structured_content["data"]
    updated = results["update_diagram"].structured_content["data"]
    assert applied["revision"] == 2
    assert {name: batched[name] for name in ("diagram_id", "revision", "applied_count")} == {
        "diagram_id": applied["id"],
        "revision": 3,
        "applied_count": 2,
    }
    assert "snapshot" not in batched
    assert "source" not in batched
    assert created_batch["revision"] == 1
    assert created_batch["applied_count"] == 2
    assert "snapshot" not in created_batch
    assert "source" not in created_batch
    assert updated["revision"] == 4

    content = results["read_diagram_content"].structured_content["data"]
    assert content["diagram_id"] == applied["id"]
    assert content["document"] == "snapshot"
    assert content["revision"] == 4
    assert content["offset"] == 0
    assert content["next_offset"] == 32
    assert content["has_more"] is True
    assert len(content["content"]) == 32


@pytest.mark.django_db(transaction=True)
def test_presents_project_and_diagram_collection_continuations(tmp_path: Path) -> None:
    setup = Client()
    category = setup.post(
        "/api/records/categories",
        data={"title": "MCP pagination", "content_schema": {"type": "object"}},
        content_type="application/json",
    )
    tag = setup.post(
        "/api/records/tags",
        data={"name": "mcp-pagination"},
        content_type="application/json",
    )
    assert category.status_code == 201
    assert tag.status_code == 201
    records = []
    for index in range(3):
        record = setup.post(
            "/api/records",
            data={
                "title": f"MCP guidance {index}",
                "content": {},
                "category_id": category.json()["id"],
                "tag_ids": [tag.json()["id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        assert record.status_code == 201
        records.append(record.json()["id"])
    scaffolding = setup.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "MCP pagination package",
            "description": "MCP pagination fixture.",
            "spec": {"language": "python", "variables": [], "templates": []},
        },
        content_type="application/json",
    )
    assert scaffolding.status_code == 201
    projects = []
    for index in range(2):
        root = tmp_path / f"project-{index}"
        root.mkdir()
        (root / "uv.lock").write_text("", encoding="utf-8")
        (root / "app.py").write_text("", encoding="utf-8")
        discovery = setup.post(
            "/api/projects/discoveries",
            data={"root": str(root)},
            content_type="application/json",
        )
        assert discovery.status_code == 200
        project = setup.post(
            "/api/projects",
            data={
                "discovery": discovery.json(),
                "architecture_root": str(root),
                "boundaries_yaml": EXAMPLE_BOUNDARIES_YAML,
                "shape_yaml": EXAMPLE_HEALTHY_SHAPE_YAML,
                "scaffolding_id": scaffolding.json()["id"],
                "record_ids": [records[0]] if index == 0 else [],
            },
            content_type="application/json",
        )
        assert project.status_code == 201
        projects.append(project.json()["project"])
    project = projects[0]
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    bound = setup.post(
        f"/api/projects/{project['id']}/workspaces",
        data={"root": str(worktree), "architecture_root": str(worktree)},
        content_type="application/json",
    )
    scopes = setup.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": records[:2]},
        content_type="application/json",
    )
    relationships = setup.put(
        f"/api/projects/{project['id']}/guidance-relationships",
        data={
            "relationships": [
                {
                    "source_record_id": source,
                    "target_record_id": target,
                    "kind": "containment",
                }
                for source, target in zip(records[:2], records[1:], strict=True)
            ]
        },
        content_type="application/json",
    )
    assert bound.status_code == 201
    assert scopes.status_code == 200
    assert relationships.status_code == 200
    diagram_sets = []
    for index in range(2):
        diagram_set = setup.post(
            "/api/diagram-sets",
            data={"title": f"MCP set {index}", "description": "Pagination"},
            content_type="application/json",
        )
        assert diagram_set.status_code == 201
        diagram_sets.append(diagram_set.json())
    diagram_set = diagram_sets[0]
    for index in range(2):
        diagram = setup.post(
            f"/api/diagram-sets/{diagram_set['id']}/diagrams",
            data={"title": f"MCP diagram {index}", "kind": "flowchart"},
            content_type="application/json",
        )
        assert diagram.status_code == 201

    identities = {
        "find_projects": {},
        "find_workspaces": {"project_id": project["id"]},
        "find_guidance_scopes": {"project_id": project["id"]},
        "find_guidance_relationships": {"project_id": project["id"]},
        "find_project_architecture_configurations": {"project_id": project["id"]},
        "find_diagram_sets": {},
        "find_diagrams": {},
        "find_diagram_set_diagrams": {"diagram_set_id": diagram_set["id"]},
    }
    results = asyncio.run(PublicMcpClient(PublicCompositeApplication()).collection_pages(identities))

    for operation, (first, final, empty) in results.items():
        for page, result in zip(("first", "final", "empty"), (first, final, empty), strict=True):
            assertion = f"{operation}:{page}"
            assert result.is_error is False, assertion
            assert result.structured_content["status"] == "ok", assertion
            assert result.structured_content["data"].get("reason") != "presentation_incomplete", assertion
            assert len(result.content[0].text.encode("utf-8")) <= 16_384, assertion
            assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192, assertion

        first_data = first.structured_content["data"]
        assert len(first_data["items"]) == 1, operation
        assert first_data["next_offset"] == 1, operation
        assert first_data["limit"] == 1, operation
        if operation == "find_project_architecture_configurations":
            assert first_data["has_more"] is False
            assert first.structured_content["follow_ups"] == []
        else:
            assert first_data["has_more"] is True, operation
            assert first.structured_content["follow_ups"] == [
                {
                    "operation_id": operation,
                    "arguments": {**identities[operation], "offset": 1, "limit": 1},
                }
            ]

        final_data = final.structured_content["data"]
        assert len(final_data["items"]) == 1, operation
        assert final_data["has_more"] is False, operation
        assert final.structured_content["follow_ups"] == [], operation
        empty_data = empty.structured_content["data"]
        assert empty_data["items"] == [], operation
        assert empty_data["has_more"] is False, operation
        assert empty_data["limit"] == 1, operation
        assert empty_data["next_offset"] == final_data["next_offset"], operation
        assert empty.structured_content["follow_ups"] == [], operation


@pytest.mark.django_db(transaction=True)
def test_presents_large_diagram_as_siren_summary_with_bounded_content_follow_up() -> None:
    setup = Client()
    diagram_set = setup.post(
        "/api/diagram-sets",
        data={"title": "Large diagrams", "description": "Siren projection boundary."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201
    diagram = setup.post(
        f"/api/diagram-sets/{diagram_set.json()['id']}/diagrams",
        data={"title": "Large flow", "kind": "flowchart"},
        content_type="application/json",
    )
    assert diagram.status_code == 201
    revision = diagram.json()["revision"]
    for index in range(20):
        operation = "add_start" if index == 0 else "add_end" if index == 19 else "add_node"
        applied = setup.post(
            f"/api/diagrams/{diagram.json()['id']}/commands",
            data={
                "expected_revision": revision,
                "operation": operation,
                "arguments": {"id": f"node-{index}", "label": "x" * 2_000},
            },
            content_type="application/json",
        )
        assert applied.status_code == 200
        revision = applied.json()["revision"]
    for index in range(19):
        applied = setup.post(
            f"/api/diagrams/{diagram.json()['id']}/commands",
            data={
                "expected_revision": revision,
                "operation": "add_flow",
                "arguments": {
                    "id": f"flow-{index}",
                    "source_id": f"node-{index}",
                    "target_id": f"node-{index + 1}",
                },
            },
            content_type="application/json",
        )
        assert applied.status_code == 200
        revision = applied.json()["revision"]
    source = applied.json()["source"]
    client = PublicMcpClient(PublicCompositeApplication())

    result = asyncio.run(client.call_tool("get_diagram", {"diagram_id": diagram.json()["id"]}))
    data = result.structured_content["data"]
    action_names = {action["name"] for action in data["actions"]}

    assert result.is_error is False
    assert result.structured_content["status"] == "ok"
    assert data["source"] == f"{source[:509]}..."
    assert data["snapshot"]["kind"] == "flowchart"
    assert data["snapshot"]["draft"] is False
    assert data["snapshot"]["elements"] == {"summary": "collection", "count": 20}
    assert "read_diagram_content" in action_names
    assert len(json.dumps(result.structured_content).encode("utf-8")) <= 8_192

    content = asyncio.run(
        PublicMcpClient(PublicCompositeApplication()).call_tool(
            "read_diagram_content",
            {
                "diagram_id": diagram.json()["id"],
                "document": "source",
                "expected_revision": revision,
                "offset": 1024,
                "limit": 512,
            },
        )
    )
    assert content.structured_content["status"] == "ok"
    assert content.structured_content["data"]["content"] == source[1024:1536]
    assert content.structured_content["data"]["next_offset"] == 1536


def test_serves_rest_and_mcp_from_the_composite_application() -> None:
    rest_response, result = asyncio.run(PublicMcpClient(application).call_tool_with_rest())

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert result.structured_content["status"] == "incomplete"
    assert result.structured_content["data"]["id"] == "python"
    assert result.structured_content["data"]["reason"] == "presentation_incomplete"
    assert "Bounded operation receipt" in result.content[0].text
