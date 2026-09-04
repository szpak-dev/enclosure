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


def test_serves_rest_and_mcp_from_the_composite_application() -> None:
    rest_response, result = asyncio.run(PublicMcpClient(application).call_tool_with_rest())

    assert rest_response.status_code == 200
    assert result.is_error is False
    assert result.structured_content["status"] == "incomplete"
    assert result.structured_content["data"]["id"] == "python"
    assert result.structured_content["data"]["reason"] == "presentation_incomplete"
    assert "Bounded operation receipt" in result.content[0].text
