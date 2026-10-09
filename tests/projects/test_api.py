import asyncio
import json
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from errno import ENXIO
from hashlib import sha256
from pathlib import Path
from time import monotonic, sleep
from typing import cast

import pytest
from django.conf import settings
from django.test import Client
from django.test.utils import override_settings
from modwire.application import ModwireApplication, ScanPolicy
from starlette.types import ASGIApp, Message, Scope

from enclosure.core.asgi import ApplicationFactory

pytestmark = pytest.mark.django_db

BOUNDARIES_YAML = """boundaries:
  tags:
    - name: module
      match: "*"
  flow:
    module_tag: module
    layers: []
    analyzers: []
"""
COMPLETE_BOUNDARIES_YAML = """excluded_patterns:
  - .dev/**
boundaries:
  tags:
    - name: example-module
      match: "*"
    - name: example-entrypoint
      match: app.py
  rules:
    - realm: example-project
      source: example-module
      allow: [example-module]
  flow:
    standalone_tags: [example-entrypoint]
    realms:
      - name: example-project
        module_tag: example-module
    analyzers: []
"""
FLOW_BOUNDARIES_YAML = """boundaries:
  tags:
    - name: example-module
      match: "src/*"
  flow:
    module_tag: example-module
    analyzers: [module-boundaries]
"""
HEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 1
"""
UNHEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 0
"""
COMPLETE_SHAPE_YAML = """shape:
  realms:
    - name: example-project
      match: "*"
      excluded_patterns:
        - tests/fixtures/**
      shape:
        max_classes_per_file: 1
"""


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def dependencies(client: Client) -> dict[str, str]:
    category = client.post(
        "/api/records/categories",
        data={"title": "Project context", "content_schema": {"type": "object"}},
        content_type="application/json",
    )
    assert category.status_code == 201

    tag = client.post(
        "/api/records/tags",
        data={"name": "project"},
        content_type="application/json",
    )
    assert tag.status_code == 201

    record = client.post(
        "/api/records",
        data={
            "title": "Project context",
            "content": {},
            "category_id": category.json()["id"],
            "tag_ids": [tag.json()["id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert record.status_code == 201

    scaffolding = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Project package",
            "description": "Creates a project package.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [
                    {
                        "path": "src/package/__init__.py",
                        "content": "",
                        "write_mode": "overwrite",
                    },
                ],
            },
        },
        content_type="application/json",
    )
    assert scaffolding.status_code == 201

    return {
        "category_id": category.json()["id"],
        "record_id": record.json()["id"],
        "scaffolding_id": scaffolding.json()["id"],
        "tag_id": tag.json()["id"],
    }


def discover(client: Client, root: Path) -> dict:
    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(root)},
        content_type="application/json",
    )
    assert response.status_code == 200
    return response.json()


def registration(
    discovery: dict,
    dependencies: dict[str, str],
    shape_yaml: str = HEALTHY_SHAPE_YAML,
) -> dict:
    return {
        "discovery": discovery,
        "architecture_root": discovery["root"],
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": shape_yaml,
        "scaffolding_id": dependencies["scaffolding_id"],
        "record_ids": [dependencies["record_id"]],
    }


def python_project(root: Path) -> None:
    (root / "uv.lock").write_text("", encoding="utf-8")
    (root / "app.py").write_text("class Application:\n    pass\n", encoding="utf-8")


def distinguish_project_source(root: Path, name: str) -> None:
    identity = sha256(root.as_posix().encode("utf-8")).hexdigest()[:16]
    (root / "identity.py").write_text(f"class {name}{identity}:\n    pass\n", encoding="utf-8")


@dataclass(frozen=True)
class BlockingArchitectureSource:
    path: Path

    @classmethod
    def create(cls, root: Path) -> "BlockingArchitectureSource":
        (root / "uv.lock").write_text("", encoding="utf-8")
        path = root / "app.py"
        os.mkfifo(path)
        return cls(path=path)

    async def connect_writer_when_ready(self) -> int:
        while True:
            try:
                return os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as error:
                if error.errno != ENXIO:
                    raise
                await asyncio.sleep(0.01)

    def replace(self) -> None:
        replacement = self.path.with_name(f".{self.path.name}.replacement")
        replacement.write_text("class ExampleApplication:\n    pass\n", encoding="utf-8")
        os.replace(replacement, self.path)

    def block(self) -> None:
        replacement = self.path.with_name(f".{self.path.name}.blocking")
        os.mkfifo(replacement)
        os.replace(replacement, self.path)


@dataclass
class DisconnectingHealthRequest:
    application: ASGIApp
    path: str
    source: BlockingArchitectureSource
    disconnect_sent: asyncio.Event = field(default_factory=asyncio.Event)
    receive_count: int = 0
    writers: list[int] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    async def run(self) -> None:
        scope = cast(
            Scope,
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": self.path,
                "raw_path": self.path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [(b"host", b"testserver")],
                "client": ("127.0.0.1", 40000),
                "server": ("testserver", 80),
            },
        )
        application = asyncio.create_task(self.application(scope, self.receive, self.send))
        try:
            await asyncio.wait_for(self.disconnect_sent.wait(), timeout=15)
            await asyncio.wait_for(application, timeout=5)
        finally:
            if not application.done():
                application.cancel()
                try:
                    await application
                except asyncio.CancelledError:
                    pass
            for writer in self.writers:
                os.close(writer)
            self.source.replace()

    async def receive(self) -> Message:
        self.receive_count += 1
        if self.receive_count == 1:
            return {"type": "http.request", "body": b"", "more_body": False}
        writer = await self.source.connect_writer_when_ready()
        self.writers.append(writer)
        self.disconnect_sent.set()
        return {"type": "http.disconnect"}

    async def send(self, message: Message) -> None:
        self.messages.append(message)

    async def run_before(self, following: "DisconnectingHealthRequest") -> None:
        await self.run()
        self.source.block()
        await following.run()


@dataclass(frozen=True)
class ArchitectureContractFixture:
    client: Client
    project_id: str
    diagram_set_id: str

    def create_diagram(
        self,
        title: str,
        kind: str,
        operation: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        created = self.client.post(
            f"/api/diagram-sets/{self.diagram_set_id}/diagram-batches",
            data={
                "title": title,
                "kind": kind,
                "commands": [{"operation": operation, "arguments": arguments}],
            },
            content_type="application/json",
        )
        assert created.status_code == 201
        diagram = self.client.get(f"/api/diagrams/{created.json()['diagram_id']}")
        assert diagram.status_code == 200
        return diagram.json()

    def create_diagram_batch(
        self,
        title: str,
        kind: str,
        commands: list[dict[str, object]],
    ) -> dict[str, object]:
        created = self.client.post(
            f"/api/diagram-sets/{self.diagram_set_id}/diagram-batches",
            data={"title": title, "kind": kind, "commands": commands},
            content_type="application/json",
        )
        assert created.status_code == 201, created.json()
        diagram = self.client.get(f"/api/diagrams/{created.json()['diagram_id']}")
        assert diagram.status_code == 200
        return diagram.json()

    def publication_body(
        self,
        tree: dict[str, object],
        uml: dict[str, object],
        entity: dict[str, object],
        coverage: str = "closed",
    ) -> dict[str, object]:
        return {
            "units": [
                {
                    "key": "application",
                    "diagram_set_id": self.diagram_set_id,
                    "source_root": "src/example",
                    "coverage": coverage,
                    "diagrams": [
                        {
                            "diagram_id": tree["id"],
                            "expected_revision": tree["revision"],
                            "role": "tree",
                            "scope": "complete",
                        },
                        {
                            "diagram_id": uml["id"],
                            "expected_revision": uml["revision"],
                            "role": "uml",
                            "scope": "focused",
                        },
                        {
                            "diagram_id": entity["id"],
                            "expected_revision": entity["revision"],
                            "role": "entity",
                            "scope": "complete",
                        },
                    ],
                    "exclusions": [{"path": "src/example/generated", "reason": "Generated source."}],
                }
            ]
        }

    def publish_example_architecture(
        self,
        entity_attributes: tuple[dict[str, object], ...] = (),
        coverage: str = "declared",
        value_type: dict[str, object] | None = None,
    ) -> dict[str, object]:
        identity = "src/example/service.py::class:src/example/service.ExampleService"
        tree = self.create_diagram_batch(
            "Example structure",
            "treeView-beta",
            [
                {"operation": "add_directory", "arguments": {"id": "source", "label": "src"}},
                {"operation": "add_directory", "arguments": {"id": "example", "label": "example"}},
                {"operation": "add_file", "arguments": {"id": "service", "label": "service.py"}},
                {"operation": "add_file", "arguments": {"id": "models", "label": "models.py"}},
                {
                    "operation": "add_branch",
                    "arguments": {"id": "source-example", "parent_id": "source", "child_id": "example"},
                },
                {
                    "operation": "add_branch",
                    "arguments": {"id": "example-service", "parent_id": "example", "child_id": "service"},
                },
                {
                    "operation": "add_branch",
                    "arguments": {"id": "example-models", "parent_id": "example", "child_id": "models"},
                },
            ],
        )
        uml = self.create_diagram(
            "Example services",
            "classDiagram",
            "add_class",
            {
                "id": identity,
                "label": "ExampleService",
                "attributes": [
                    {
                        "name": "value",
                        "type": value_type or {"name": "String"},
                        "visibility": "public",
                        "static": False,
                    }
                ],
                "methods": [
                    {
                        "name": "execute",
                        "parameters": [{"name": "request", "type": {"name": "String"}}],
                        "return_type": {"name": "String"},
                        "visibility": "public",
                        "modifier": "instance",
                    }
                ],
            },
        )
        entity_id = "example-record"
        entity_commands: list[dict[str, object]] = [
            {"operation": "add_entity", "arguments": {"id": entity_id, "label": "EXAMPLE_RECORD"}},
            {
                "operation": "add_attribute",
                "arguments": {
                    "id": "example-record-id",
                    "label": "id",
                    "data_type": "string",
                    "entity_id": entity_id,
                    "keys": ["PK"],
                },
            },
            {
                "operation": "add_attribute",
                "arguments": {
                    "id": "example-record-name",
                    "label": "name",
                    "data_type": "string",
                    "entity_id": entity_id,
                },
            },
        ]
        entity_commands.extend(entity_attributes)
        entity = self.create_diagram_batch(
            "Example entities",
            "erDiagram",
            entity_commands,
        )
        response = self.client.post(
            f"/api/projects/{self.project_id}/architecture-contract-publications",
            data=self.publication_body(tree, uml, entity, coverage),
            content_type="application/json",
        )
        assert response.status_code == 201, response.json()
        return response.json()

    def accept_publication(self, publication: dict[str, object]) -> dict[str, object]:
        binding = self.client.get(f"/api/projects/{self.project_id}/operating-contract-binding")
        assert binding.status_code == 200, binding.json()
        value = binding.json()
        record_ids = [
            reference["id"]
            for reference in value["effective_revision"]["references"]
            if reference["kind"] == "guidance"
        ]
        response = self.client.post(
            f"/api/projects/operating-contracts/{value['contract']['id']}/revisions",
            data={
                "record_ids": record_ids,
                "references": [
                    {
                        "kind": "architecture",
                        "id": publication["id"],
                        "authority": publication["authority"],
                        "revision": publication["revision"],
                    }
                ],
            },
            content_type="application/json",
        )
        assert response.status_code == 201, response.json()
        return response.json()


def create_architecture_contract_fixture(
    client: Client,
    dependencies: dict[str, str],
    root: Path,
) -> ArchitectureContractFixture:
    python_project(root)
    registered = client.post(
        "/api/projects",
        data=registration(discover(client, root), dependencies),
        content_type="application/json",
    )
    assert registered.status_code == 201
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Example architecture", "description": "Accepted example contract diagrams."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201
    return ArchitectureContractFixture(client, registered.json()["project"]["id"], diagram_set.json()["id"])


def architecture_project_source(
    root: Path,
    name_field: str = "models.CharField(max_length=120)",
    request_annotation: str = "str",
    value_annotation: str = "str",
    duplicate_service_name: bool = False,
    include_execute: bool = True,
) -> None:
    source = root / "src" / "example" / "service.py"
    source.parent.mkdir(parents=True)
    execute = (
        f"    def execute(self, request: {request_annotation}) -> str:\n        return request\n"
        if include_execute
        else ""
    )
    source.write_text(
        f"import typing\n\nclass ExampleService:\n    value: {value_annotation}\n\n{execute}",
        encoding="utf-8",
    )
    model = root / "src" / "example" / "models.py"
    model.write_text(
        "from django.db import models\n\n"
        "class ExampleRecordModel(models.Model):\n"
        "    id = models.UUIDField(primary_key=True)\n"
        f"    name = {name_field}\n",
        encoding="utf-8",
    )
    if duplicate_service_name:
        (root / "src" / "example" / "other.py").write_text(
            "class ExampleService:\n"
            "    value: int\n\n"
            "    def execute(self, request: int) -> int:\n"
            "        return request\n",
            encoding="utf-8",
        )


def implementation_document(
    root: Path,
    name_field: str = "models.CharField(max_length=120)",
    request_annotation: str = "str",
    value_annotation: str = "str",
    duplicate_service_name: bool = False,
    include_execute: bool = True,
) -> dict[str, object]:
    architecture_project_source(
        root,
        name_field,
        request_annotation,
        value_annotation,
        duplicate_service_name,
        include_execute,
    )
    application = ModwireApplication.create()
    code_map = application.generate_map("python", str(root), ScanPolicy(excluded_patterns=("app.py",)))
    document = application.implementation_manifest(code_map, application.implementation_manifest_formats()[0])
    return document.model_dump(mode="json")


def accept_health_architecture(
    client: Client,
    root: Path,
    resolution: dict,
    coverage: str = "declared",
) -> dict:
    architecture_project_source(root)
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Example health architecture", "description": "Accepted example health contract."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201, diagram_set.json()
    fixture = ArchitectureContractFixture(
        client,
        resolution["project"]["id"],
        diagram_set.json()["id"],
    )
    publication = fixture.publish_example_architecture(coverage=coverage)
    fixture.accept_publication(publication)
    return resolution


@pytest.mark.django_db
def test_discovers_python_project_without_changing_its_root(client: Client, tmp_path: Path) -> None:
    python_project(tmp_path)

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "root": str(tmp_path),
        "stack": {
            "language": "python",
            "language_version": "",
            "package_manager": "uv",
        },
    }


@pytest.mark.django_db
def test_discovery_rejects_missing_directory(client: Client, tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(missing)},
        content_type="application/json",
    )

    assert response.status_code == 422, response.json()
    assert response.json() == {"detail": f"Invalid project root: {missing}"}


@pytest.mark.django_db
def test_discovery_rejects_project_without_package_manager(client: Client, tmp_path: Path) -> None:
    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 422, response.json()
    assert response.json() == {"detail": "Package manager could not be recognized."}


@pytest.mark.django_db
def test_discovery_rejects_ambiguous_package_managers(client: Client, tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Ambiguous package manager: ")
    assert "python/uv" in response.json()["detail"]
    assert "typescript/npm" in response.json()["detail"]


@pytest.mark.django_db
def test_registers_discovered_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json() == {
        "project": {
            "id": response.json()["project"]["id"],
            "title": tmp_path.name,
            "language_id": "python",
            "language_version": "",
            "package_manager_id": "uv",
            "scaffolding_id": dependencies["scaffolding_id"],
        },
        "workspace": {
            "id": response.json()["workspace"]["id"],
            "project_id": response.json()["project"]["id"],
            "root": str(tmp_path),
            "architecture_root": str(tmp_path),
            "revision": 1,
        },
    }


@pytest.mark.django_db
def test_publishes_immutable_project_architecture_contract_evidence(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    registered = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Example architecture", "description": "Accepted example contract diagrams."},
        content_type="application/json",
    ).json()
    fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
    tree = fixture.create_diagram(
        "Example structure",
        "treeView-beta",
        "add_directory",
        {"id": "source", "label": "example"},
    )
    uml = fixture.create_diagram(
        "Example services",
        "classDiagram",
        "add_class",
        {"id": "service", "label": "ExampleService"},
    )
    entity = fixture.create_diagram(
        "Example storage",
        "erDiagram",
        "add_entity",
        {"id": "record", "label": "EXAMPLE_RECORD"},
    )

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications",
        data=fixture.publication_body(tree, uml, entity),
        content_type="application/json",
    )

    assert response.status_code == 201
    publication = response.json()
    openapi = client.get("/api/openapi.json").json()
    assert (
        openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications"]["post"]["operationId"]
        == "publish_project_architecture_contract"
    )
    assert (
        openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications/{publication_id}"]["get"][
            "operationId"
        ]
        == "get_project_architecture_contract"
    )
    assert (
        openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications/{publication_id}/manifest"][
            "get"
        ]["operationId"]
        == "compile_project_architecture_manifest"
    )
    assert (
        openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications/{publication_id}/comparisons"][
            "post"
        ]["operationId"]
        == "compare_project_architecture_manifest"
    )
    assert publication["project_id"] == fixture.project_id
    assert publication["version"] == 1
    assert publication["authority"] == f"project:{fixture.project_id}:architecture-contract"
    assert len(publication["revision"]) == 64
    assert publication["units"][0]["key"] == "application"
    assert publication["units"][0]["source_root"] == "src/example"
    assert publication["units"][0]["coverage"] == "closed"
    assert publication["units"][0]["exclusions"][0]["path"] == "src/example/generated"
    accepted_diagrams = publication["units"][0]["diagrams"]
    assert [(item["role"], item["scope"], item["kind"]) for item in accepted_diagrams] == [
        ("tree", "complete", "treeView-beta"),
        ("uml", "focused", "classDiagram"),
        ("entity", "complete", "erDiagram"),
    ]
    for item in accepted_diagrams:
        canonical = json.dumps(item["snapshot"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        assert item["snapshot_digest"] == sha256(canonical.encode("utf-8")).hexdigest()
        assert item["snapshot_version"] >= 1
        assert len(item["registry_fingerprint"]) == 64

    changed = client.post(
        f"/api/diagrams/{uml['id']}/commands",
        data={
            "expected_revision": uml["revision"],
            "operation": "add_class",
            "arguments": {"id": "repository", "label": "ExampleRepository"},
        },
        content_type="application/json",
    )
    assert changed.status_code == 200
    assert changed.json()["revision"] == uml["revision"] + 1

    stored = client.get(f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}")
    assert stored.status_code == 200
    assert stored.json() == publication


@pytest.mark.django_db
def test_rejects_invalid_project_architecture_contract_members(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    registered = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Rejected architecture", "description": "Rejected contract examples."},
        content_type="application/json",
    ).json()
    fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
    tree = fixture.create_diagram(
        "Example structure",
        "treeView-beta",
        "add_directory",
        {"id": "source", "label": "example"},
    )
    uml = fixture.create_diagram(
        "Example services",
        "classDiagram",
        "add_class",
        {"id": "service", "label": "ExampleService"},
    )
    entity = fixture.create_diagram(
        "Example storage",
        "erDiagram",
        "add_entity",
        {"id": "record", "label": "EXAMPLE_RECORD"},
    )
    draft = client.post(
        f"/api/diagram-sets/{fixture.diagram_set_id}/diagrams",
        data={"title": "Draft structure", "kind": "treeView-beta"},
        content_type="application/json",
    ).json()
    url = f"/api/projects/{fixture.project_id}/architecture-contract-publications"

    draft_body = fixture.publication_body(draft, uml, entity)
    rejected_draft = client.post(url, data=draft_body, content_type="application/json")
    assert rejected_draft.status_code == 422
    assert rejected_draft.json() == {"detail": f"Architecture diagram {draft['id']!r} is still a draft."}

    unsupported_body = fixture.publication_body(entity, uml, tree)
    rejected_kind = client.post(url, data=unsupported_body, content_type="application/json")
    assert rejected_kind.status_code == 422
    assert "role 'tree' requires 'treeView-beta'" in rejected_kind.json()["detail"]

    stale_body = fixture.publication_body(tree, uml, entity)
    stale_body["units"][0]["diagrams"][0]["expected_revision"] = tree["revision"] + 1
    rejected_stale = client.post(url, data=stale_body, content_type="application/json")
    assert rejected_stale.status_code == 422
    assert rejected_stale.json() == {
        "detail": f"Architecture diagram {tree['id']!r} could not be resolved at revision {tree['revision'] + 1}."
    }

    missing_body = fixture.publication_body(tree, uml, entity)
    missing_body["units"][0]["diagrams"][2]["diagram_id"] = "missing"
    rejected_missing = client.post(url, data=missing_body, content_type="application/json")
    assert rejected_missing.status_code == 422
    assert rejected_missing.json() == {
        "detail": f"Architecture diagram 'missing' could not be resolved at revision {entity['revision']}."
    }

    duplicate_body = fixture.publication_body(tree, uml, entity)
    duplicate_body["units"][0]["diagrams"].append(duplicate_body["units"][0]["diagrams"][1])
    rejected_duplicate = client.post(url, data=duplicate_body, content_type="application/json")
    assert rejected_duplicate.status_code == 422
    assert rejected_duplicate.json() == {
        "detail": f"Architecture diagram {uml['id']!r} is duplicated in the publication."
    }

    exclusion_body = fixture.publication_body(tree, uml, entity)
    exclusion_body["units"][0]["exclusions"] = [{"path": "../generated", "reason": "Outside the unit."}]
    rejected_exclusion = client.post(url, data=exclusion_body, content_type="application/json")
    assert rejected_exclusion.status_code == 422
    assert rejected_exclusion.json() == {
        "detail": "Architecture exclusion '../generated' is not a normalized relative path."
    }


@pytest.mark.django_db
def test_rejects_conflicting_architecture_assertions_before_publication(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    registered = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Example candidate", "description": "Example candidate contract diagrams."},
        content_type="application/json",
    ).json()
    fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
    tree = fixture.create_diagram(
        "Example structure",
        "treeView-beta",
        "add_directory",
        {"id": "source", "label": "example"},
    )
    uml = fixture.create_diagram_batch(
        "Example services",
        "classDiagram",
        [
            {"operation": "add_class", "arguments": {"id": "source", "label": "ExampleSource"}},
            {"operation": "add_class", "arguments": {"id": "target", "label": "ExampleTarget"}},
            {
                "operation": "add_relation",
                "arguments": {
                    "id": "r1",
                    "source_id": "source",
                    "target_id": "target",
                    "relation_kind": "dependency",
                },
            },
        ],
    )
    entity = fixture.create_diagram_batch(
        "Example entities",
        "erDiagram",
        [
            {"operation": "add_entity", "arguments": {"id": "source", "label": "EXAMPLE_SOURCE"}},
            {"operation": "add_entity", "arguments": {"id": "target", "label": "EXAMPLE_TARGET"}},
            {
                "operation": "add_relationship",
                "arguments": {
                    "id": "r1",
                    "source_id": "source",
                    "target_id": "target",
                    "label": "example relation",
                },
            },
        ],
    )
    url = f"/api/projects/{fixture.project_id}/architecture-contract-publications"
    conflicting = client.post(
        url,
        data=fixture.publication_body(tree, uml, entity),
        content_type="application/json",
    )

    assert conflicting.status_code == 422
    assert conflicting.json() == {
        "detail": "Architecture assertion identity 'relationship:r1' has conflicting declarations."
    }

    valid_body = fixture.publication_body(tree, uml, entity)
    valid_body["units"][0]["diagrams"] = valid_body["units"][0]["diagrams"][:2]
    accepted = client.post(url, data=valid_body, content_type="application/json")

    assert accepted.status_code == 201, accepted.json()
    assert accepted.json()["version"] == 1


@pytest.mark.django_db
def test_manifest_compilation_keeps_uml_members_separate_from_entity_fields(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture(
        (
            {
                "operation": "add_attribute",
                "arguments": {
                    "id": "entity-value",
                    "label": "value",
                    "data_type": "int",
                    "entity_id": "example-record",
                },
            },
        )
    )

    response = client.get(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"
    )

    assert response.status_code == 200, response.json()
    assertions = response.json()["units"][0]["assertions"]
    assert any(item["kind"] == "member" and item["name"] == "value" for item in assertions)
    assert any(item["kind"] == "entity_field" and item["name"] == "value" for item in assertions)


@pytest.mark.django_db
def test_comparison_rejects_a_tampered_modwire_document(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path)
    document["digest"] = "0" * 64

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 422, response.json()
    assert "digest does not match its payload" in response.json()["detail"]


@pytest.mark.django_db
def test_comparison_rejects_multiple_parameter_type_annotations_as_a_mismatch(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path)
    payload = json.loads(str(document["payload"]))
    parameter_annotation = next(
        annotation for annotation in payload["annotations"] if annotation["role"] == "parameter_type"
    )
    payload["annotations"].append(parameter_annotation | {"expression": "int"})
    payload["annotations"].sort(
        key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    )
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    document["payload"] = canonical
    document["digest"] = sha256(canonical.encode("utf-8")).hexdigest()

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    parameter_failures = [
        result
        for result in comparison["results"]
        if result["assertion_kind"] == "member"
        and result["state"] == "fail"
        and result["expected"]["fields"]["name"] == "execute"
    ]
    assert comparison["conclusion"] == "does_not_conform"
    assert [result["kind"] for result in parameter_failures] == ["mismatched"], comparison
    assert "owner_id" not in parameter_failures[0]["expected"]["fields"]
    assert "owner_id" not in parameter_failures[0]["observed"][0]["fields"]


@pytest.mark.django_db
def test_public_comparison_excludes_python_annotated_metadata_from_parameter_type(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(
        tmp_path,
        request_annotation="typing.Annotated[str, object()]",
    )

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    assert comparison["conclusion"] == "conforms", comparison
    assert comparison["failed"] == 0
    assert comparison["unverified"] == 0
    assert all(result["state"] == "pass" for result in comparison["results"])


@pytest.mark.django_db
def test_public_comparison_translates_python_callable_signature(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture(value_type={"name": "Callable"})
    document = implementation_document(
        tmp_path,
        value_annotation="typing.Callable[[str], int]",
    )

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    assert comparison["conclusion"] == "conforms", comparison
    assert comparison["failed"] == 0
    assert comparison["unverified"] == 0


@pytest.mark.django_db
def test_public_comparison_prefers_exact_classifier_reference_over_duplicate_name(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path, duplicate_service_name=True)

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    assert comparison["conclusion"] == "conforms", comparison
    assert comparison["failed"] == 0
    assert comparison["unverified"] == 0


@pytest.mark.django_db
def test_public_comparison_reports_missing_member_from_complete_inventory(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path, include_execute=False)

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    missing = [
        result
        for result in comparison["results"]
        if result["assertion_kind"] == "member" and result["state"] == "fail" and result["kind"] == "missing"
    ]
    assert comparison["conclusion"] == "does_not_conform"
    assert comparison["failed"] == 1
    assert comparison["unverified"] == 0
    assert len(missing) == 1


@pytest.mark.django_db
def test_public_comparison_normalizes_python_abc_strategy_realization(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    registered = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    assert registered.status_code == 201, registered.json()
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Relationship architecture", "description": "Exact relationship realization."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201, diagram_set.json()
    fixture = ArchitectureContractFixture(client, registered.json()["project"]["id"], diagram_set.json()["id"])
    source = tmp_path / "src" / "example"
    source.mkdir(parents=True)
    (source / "base.py").write_text(
        "from abc import ABC, abstractmethod\n\n"
        "class ExampleBase(ABC):\n"
        "    @abstractmethod\n"
        "    def execute(self) -> None:\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )
    (source / "service.py").write_text(
        "from .base import ExampleBase\n\n"
        "class ExampleService(ExampleBase):\n"
        "    def execute(self) -> None:\n"
        "        return None\n",
        encoding="utf-8",
    )
    (source / "models.py").write_text(
        "from django.db import models\n\n"
        "class ExampleRecordModel(models.Model):\n"
        "    id = models.UUIDField(primary_key=True)\n"
        "    name = models.CharField(max_length=120)\n",
        encoding="utf-8",
    )
    tree = fixture.create_diagram_batch(
        "Relationship structure",
        "treeView-beta",
        [
            {"operation": "add_directory", "arguments": {"id": "source", "label": "src"}},
            {"operation": "add_directory", "arguments": {"id": "example", "label": "example"}},
            {"operation": "add_file", "arguments": {"id": "base", "label": "base.py"}},
            {"operation": "add_file", "arguments": {"id": "service", "label": "service.py"}},
            {"operation": "add_file", "arguments": {"id": "models", "label": "models.py"}},
            {
                "operation": "add_branch",
                "arguments": {"id": "source-example", "parent_id": "source", "child_id": "example"},
            },
            {
                "operation": "add_branch",
                "arguments": {"id": "example-base", "parent_id": "example", "child_id": "base"},
            },
            {
                "operation": "add_branch",
                "arguments": {"id": "example-service", "parent_id": "example", "child_id": "service"},
            },
            {
                "operation": "add_branch",
                "arguments": {"id": "example-models", "parent_id": "example", "child_id": "models"},
            },
        ],
    )
    base_id = "src/example/base.py::class:src/example/base.ExampleBase"
    service_id = "src/example/service.py::class:src/example/service.ExampleService"
    uml = fixture.create_diagram_batch(
        "Relationship services",
        "classDiagram",
        [
            {
                "operation": "add_class",
                "arguments": {"id": base_id, "label": "ExampleBase", "annotations": ["abstract"]},
            },
            {"operation": "add_class", "arguments": {"id": service_id, "label": "ExampleService"}},
            {
                "operation": "add_relation",
                "arguments": {
                    "id": "service-inherits-base",
                    "source_id": service_id,
                    "target_id": base_id,
                    "relation_kind": "realization",
                },
            },
        ],
    )
    entity = fixture.create_diagram_batch(
        "Relationship entities",
        "erDiagram",
        [
            {"operation": "add_entity", "arguments": {"id": "record", "label": "EXAMPLE_RECORD"}},
            {
                "operation": "add_attribute",
                "arguments": {
                    "id": "record-id",
                    "label": "id",
                    "data_type": "string",
                    "entity_id": "record",
                    "keys": ["PK"],
                },
            },
            {
                "operation": "add_attribute",
                "arguments": {
                    "id": "record-name",
                    "label": "name",
                    "data_type": "string",
                    "entity_id": "record",
                },
            },
        ],
    )
    publication = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications",
        data=fixture.publication_body(tree, uml, entity, coverage="declared"),
        content_type="application/json",
    )
    assert publication.status_code == 201, publication.json()
    application = ModwireApplication.create()
    code_map = application.generate_map("python", str(tmp_path), ScanPolicy(excluded_patterns=("app.py",)))
    document = application.implementation_manifest(code_map, application.implementation_manifest_formats()[0])

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication.json()['id']}/comparisons",
        data={"implementation_document": document.model_dump(mode="json")},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    assert comparison["conclusion"] == "conforms", comparison
    assert comparison["failed"] == 0
    assert comparison["unverified"] == 0


@pytest.mark.django_db
def test_compiled_architecture_manifest_is_stable_at_the_public_gate(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    url = f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"

    first = client.get(url)
    second = client.get(url)

    assert first.status_code == 200, first.json()
    assert second.status_code == 200, second.json()
    assert first.json() == second.json()
    assert len(first.json()["digest"]) == 64


@pytest.mark.django_db
def test_compiled_architecture_manifest_preserves_the_complete_attribute_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()

    response = client.get(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"
    )

    assert response.status_code == 200, response.json()
    attribute = next(
        assertion
        for assertion in response.json()["units"][0]["assertions"]
        if assertion["kind"] == "member" and assertion["name"] == "value"
    )
    assert {
        "name": attribute["name"],
        "type": attribute["type"],
        "visibility": attribute["visibility"],
        "ownership": attribute["ownership"],
    } == {
        "name": "value",
        "type": {"name": "String", "arguments": [], "cardinality": "one"},
        "visibility": "public",
        "ownership": "instance",
    }


@pytest.mark.django_db
def test_public_comparison_reports_language_neutral_entity_field_drift(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path, "models.IntegerField()")

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    failures = [
        result
        for result in comparison["results"]
        if result["assertion_kind"] == "entity_field" and result["state"] == "fail"
    ]
    assert comparison["conclusion"] == "does_not_conform"
    assert len(failures) == 1, comparison
    assert failures[0]["owner"] == "implementation"
    assert failures[0]["expected"]["fields"]["type"]["name"] == "string"
    assert failures[0]["observed"][0]["fields"]["type"]["name"] == "int"
    assert "IntegerField" not in json.dumps(comparison)


@pytest.mark.django_db
def test_public_comparison_accepts_language_neutral_entity_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    document = implementation_document(tmp_path)

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    assert comparison["conclusion"] == "conforms", json.dumps(
        [result for result in comparison["results"] if result["state"] != "pass"],
        indent=2,
    )
    assert comparison["failed"] == 0
    assert comparison["unverified"] == 0
    assert all(result["state"] == "pass" for result in comparison["results"])
    entity_results = [
        result for result in comparison["results"] if result["assertion_kind"] in {"entity", "entity_field"}
    ]
    assert len(entity_results) == 3


@pytest.mark.django_db
def test_closed_comparison_does_not_treat_an_external_import_as_unexpected(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture(coverage="closed")
    document = implementation_document(tmp_path)

    response = client.post(
        f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
        data={"implementation_document": document},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    comparison = response.json()
    relationship_failures = [
        result
        for result in comparison["results"]
        if result["assertion_kind"] == "relationship" and result["state"] == "fail"
    ]
    assert relationship_failures == []


@pytest.mark.django_db
def test_publishes_and_binds_versioned_operating_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    contract_response = client.post(
        "/api/projects/operating-contracts",
        data={
            "title": "Example Python delivery contract",
            "authority": "example:engineering:python-delivery",
            "provenance": "example-repository",
        },
        content_type="application/json",
    )
    assert contract_response.status_code == 201
    contract = contract_response.json()

    first_response = client.post(
        f"/api/projects/operating-contracts/{contract['id']}/revisions",
        data={
            "record_ids": [dependencies["record_id"]],
            "references": [
                {
                    "kind": "policy",
                    "id": "example-python-policy",
                    "authority": "example:policy:python",
                    "revision": "3",
                }
            ],
        },
        content_type="application/json",
    )
    assert first_response.status_code == 201
    first = first_response.json()
    assert first["version"] == 1
    assert [reference["kind"] for reference in first["references"]] == ["guidance", "policy"]

    second_response = client.post(
        f"/api/projects/operating-contracts/{contract['id']}/revisions",
        data={
            "record_ids": [dependencies["record_id"]],
            "references": [
                {
                    "kind": "architecture",
                    "id": "example-python-architecture",
                    "authority": "example:architecture:python",
                    "revision": "5",
                }
            ],
        },
        content_type="application/json",
    )
    assert second_response.status_code == 201
    assert second_response.json()["version"] == 2
    assert client.get(f"/api/projects/operating-contracts/{contract['id']}/revisions/1").json() == first

    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = []
    project_response = client.post("/api/projects", data=payload, content_type="application/json")
    assert project_response.status_code == 201
    project = project_response.json()["project"]

    unconfigured = client.get(f"/api/projects/{project['id']}/operating-contract-binding")
    assert unconfigured.status_code == 409
    assert unconfigured.json() == {"state": "unconfigured", "project_id": project["id"]}
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )
    assert context.status_code == 200
    assert context.json()["readiness"] == "incomplete"
    assert context.json()["receipt"]["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"

    binding_data = {
        "contract_id": contract["id"],
        "version": 1,
        "update_policy": "pinned",
    }
    bound = client.post(
        f"/api/projects/{project['id']}/operating-contract-bindings",
        data=binding_data,
        content_type="application/json",
    )
    assert bound.status_code == 201
    assert bound.json()["effective_revision"]["version"] == 1
    duplicate = client.post(
        f"/api/projects/{project['id']}/operating-contract-bindings",
        data={**binding_data, "version": 2},
        content_type="application/json",
    )
    assert duplicate.status_code == 422

    replaced = client.put(
        f"/api/projects/{project['id']}/operating-contract-binding",
        data={**binding_data, "update_policy": "follow-latest"},
        content_type="application/json",
    )
    assert replaced.status_code == 200
    assert replaced.json()["bound_revision"] == 1
    assert replaced.json()["effective_revision"]["version"] == 2


@pytest.mark.django_db
def test_registration_rejects_invalid_architecture_yaml(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies, shape_yaml="shape: [")

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Invalid architecture configuration:")


@pytest.mark.django_db
def test_registration_accepts_complete_architecture_configuration(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies, shape_yaml=COMPLETE_SHAPE_YAML)
    payload["boundaries_yaml"] = COMPLETE_BOUNDARIES_YAML

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 201


@pytest.mark.django_db
def test_lists_and_fetches_registered_projects(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    assert created.status_code == 201
    resolution = created.json()
    project = resolution["project"]

    listed = client.get("/api/projects")
    found = client.post(
        "/api/projects/root-search-results",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )
    fetched = client.get(f"/api/projects/{project['id']}")

    assert listed.status_code == 200
    assert listed.json()["items"] == [{"id": project["id"], "title": project["title"]}]
    assert found.status_code == 200
    assert found.json() == project
    assert resolved.status_code == 200
    assert resolved.json() == resolution
    assert fetched.status_code == 200
    assert fetched.json() == project


@pytest.mark.django_db
def test_binds_multiple_worktrees_and_uses_the_selected_workspace(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    approve_operation,
) -> None:
    main = tmp_path / "main"
    feature = tmp_path / "feature"
    main.mkdir()
    feature.mkdir()
    python_project(main)
    python_project(feature)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, main), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]

    bound = client.post(
        f"/api/projects/{project['id']}/workspaces",
        data={"root": str(feature), "architecture_root": str(feature)},
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(feature)},
        content_type="application/json",
    )
    generated = client.post(
        f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )
    workspaces = client.get(f"/api/projects/{project['id']}/workspaces")
    fetched = client.get(f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}")
    deleted = client.delete(
        f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}",
        data={"expected_revision": 1},
        content_type="application/json",
    )
    approve_operation(client, deleted)
    deleted = client.delete(
        f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}",
        data={"expected_revision": 1},
        content_type="application/json",
    )

    assert bound.status_code == 201
    assert bound.json() == {
        "id": bound.json()["id"],
        "project_id": project["id"],
        "root": str(feature),
        "architecture_root": str(feature),
        "revision": 1,
    }
    assert resolved.status_code == 200
    assert resolved.json() == {"project": project, "workspace": bound.json()}
    assert workspaces.json()["items"] == [
        bound.json(),
        resolution["workspace"],
    ]
    assert fetched.json() == bound.json()
    assert generated.status_code == 200
    assert (feature / "generated" / "src" / "package" / "__init__.py").is_file()
    assert not (main / "generated").exists()
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project['id']}/workspaces").json()["items"] == [resolution["workspace"]]


@pytest.mark.django_db
def test_rebinds_a_moved_workspace_without_changing_project_identity_or_title(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    original = tmp_path / "original-checkout"
    relocated = tmp_path / "relocated-checkout"
    original.mkdir()
    python_project(original)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, original), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    original.rename(relocated)

    stale = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/status")
    replaced = client.put(
        f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
        data={
            "root": str(relocated),
            "architecture_root": str(relocated),
            "expected_revision": 1,
        },
        content_type="application/json",
    )
    conflicted = client.put(
        f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
        data={
            "root": str(original),
            "architecture_root": str(original),
            "expected_revision": 1,
        },
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(relocated)},
        content_type="application/json",
    )
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(relocated), "task": "Continue after moving the checkout"},
        content_type="application/json",
    )

    assert stale.status_code == 200
    assert stale.json()["state"] == "missing_root"
    assert replaced.status_code == 200
    assert replaced.json() == {
        **workspace,
        "root": str(relocated),
        "architecture_root": str(relocated),
        "revision": 2,
    }
    assert conflicted.status_code == 422
    assert conflicted.json() == {
        "detail": f"Workspace {workspace['id']!r} revision conflict: expected 1, current revision is 2."
    }
    assert resolved.json() == {"project": project, "workspace": replaced.json()}
    assert resolved.json()["project"]["title"] == "original-checkout"
    assert context.status_code == 200
    assert context.json()["project_id"] == project["id"]
    assert context.json()["guidance"][0]["id"] == dependencies["record_id"]


@pytest.mark.django_db
def test_rejects_a_workspace_root_already_bound_to_another_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    python_project(first_root)
    python_project(second_root)
    first = client.post(
        "/api/projects",
        data=registration(discover(client, first_root), dependencies),
        content_type="application/json",
    ).json()
    second = client.post(
        "/api/projects",
        data=registration(discover(client, second_root), dependencies),
        content_type="application/json",
    ).json()

    conflict = client.post(
        f"/api/projects/{second['project']['id']}/workspaces",
        data={"root": str(first_root), "architecture_root": str(first_root)},
        content_type="application/json",
    )

    assert first["project"]["id"] != second["project"]["id"]
    assert conflict.status_code == 422
    assert conflict.json() == {"detail": f"Workspace root is already bound: {first_root}"}


@pytest.mark.django_db
def test_gets_ready_workspace_context_from_linked_records(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    context = response.json()

    assert response.status_code == 200
    assert context == {
        "project_id": created["id"],
        "root": str(tmp_path),
        "readiness": "ready",
        "guidance": [
            {
                "id": dependencies["record_id"],
                "title": "Project context",
                "summary": "Project context",
                "authority": f"record:{dependencies['record_id']}",
                "revision": context["guidance"][0]["revision"],
                "schema_revision": 1,
                "current_schema_revision": 1,
                "applies_when": [],
                "guidance": [],
                "checks": [],
            }
        ],
        "receipt": {
            "authority": {
                "kind": "project-operating-contract",
                "id": f"project:{created['id']}:operating-contract",
                "revision": "1",
                "provenance": "project-registration",
            },
            "items": [
                {
                    "record_id": dependencies["record_id"],
                    "title": "Project context",
                    "requirement": "mandatory",
                    "reason": "operating-contract",
                    "explanation": "Required by the active project operating contract.",
                    "authority": f"record:{dependencies['record_id']}",
                    "revision": context["guidance"][0]["revision"],
                    "checks": [],
                }
            ],
            "required_checks": [],
            "budget": {
                "used_optional_characters": 0,
                "optional_character_limit": 4096,
            },
            "coverage": {
                "status": "complete",
                "selected_count": 1,
                "omitted_count": 0,
                "diagnostic_count": 0,
            },
            "omissions": [],
            "diagnostics": [],
            "stop_condition": "selected-guidance-and-checks",
        },
    }


@pytest.mark.django_db
def test_routes_scoped_guidance_for_representative_tasks(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    database = client.post(
        "/api/records",
        data={
            "title": "Database delivery",
            "content": {
                "summary": "Safely deliver database changes.",
                "applies_when": ["database migration"],
                "guidance": ["Prepare a rollback before applying a migration."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [
                {
                    "path": "database.md",
                    "language": "markdown",
                    "content": "database migration rollback " * 20,
                }
            ],
        },
        content_type="application/json",
    )
    python = client.post(
        "/api/records",
        data={
            "title": "Python typing",
            "content": {
                "summary": "Keep Python typing strict.",
                "applies_when": ["python typing"],
                "guidance": ["Keep public annotations precise."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [
                {
                    "path": "typing.md",
                    "language": "markdown",
                    "content": "python typing annotations",
                }
            ],
        },
        content_type="application/json",
    )
    universal = client.post(
        "/api/records",
        data={
            "title": "Database migration rollback",
            "content": {
                "summary": "Database migration rollback.",
                "guidance": ["Review the completed change."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    unscoped = client.post(
        "/api/records",
        data={
            "title": "Unscoped database policy",
            "content": {
                "summary": "Belongs to a different project.",
                "applies_when": ["database migration"],
                "guidance": ["This guidance must not leak across projects."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert {database.status_code, python.status_code, universal.status_code, unscoped.status_code} == {201}

    python_project(tmp_path)
    project = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]
    replaced = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [universal.json()["id"], database.json()["id"], python.json()["id"]]},
        content_type="application/json",
    )

    assert replaced.status_code == 200
    assert [scope["record_id"] for scope in replaced.json()] == [
        universal.json()["id"],
        database.json()["id"],
        python.json()["id"],
    ]
    assert [scope["position"] for scope in replaced.json()] == [1, 2, 3]
    assert client.get(f"/api/projects/{project['id']}/guidance-scopes").json()["items"] == replaced.json()

    corpus = (
        ("database migration rollback", database.json()["id"]),
        ("python typing annotations", python.json()["id"]),
    )
    for task, expected_id in corpus:
        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": task},
            content_type="application/json",
        )

        assert response.status_code == 200
        guidance_ids = [guidance["id"] for guidance in response.json()["guidance"]]
        assert guidance_ids == [dependencies["record_id"], expected_id, universal.json()["id"]]
        assert unscoped.json()["id"] not in guidance_ids
        assert [item["reason"] for item in response.json()["receipt"]["items"]] == [
            "operating-contract",
            "task-applicable",
            "project-default",
        ]


@override_settings(RECORDS_EMBEDDINGS_ENABLED=False)
@pytest.mark.django_db
def test_routes_optional_guidance_by_fallback_order_within_budget(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first = client.post(
        "/api/records",
        data={
            "title": "First fallback",
            "content": {
                "summary": "a" * 1800,
                "guidance": ["Keep this complete."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    second = client.post(
        "/api/records",
        data={
            "title": "Second fallback",
            "content": {
                "summary": "b" * 3000,
                "guidance": ["This whole record exceeds the remaining budget."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert first.status_code == 201
    assert second.status_code == 201

    python_project(tmp_path)
    project = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]
    scoped = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [first.json()["id"], second.json()["id"]]},
        content_type="application/json",
    )
    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Any task without ranking support"},
        content_type="application/json",
    )

    assert scoped.status_code == 200
    assert response.status_code == 200
    assert [guidance["id"] for guidance in response.json()["guidance"]] == [
        dependencies["record_id"],
        first.json()["id"],
    ]
    assert response.json()["guidance"][1]["summary"] == "a" * 1800
    assert response.json()["receipt"]["coverage"] == {
        "status": "partial",
        "selected_count": 2,
        "omitted_count": 1,
        "diagnostic_count": 0,
    }
    assert response.json()["receipt"]["omissions"] == [
        {
            "code": "optional-budget-exhausted",
            "guidance_ids": [second.json()["id"]],
            "message": "Supplemental guidance was omitted because the workspace-context budget was exhausted.",
        }
    ]
    assert response.json()["receipt"]["stop_condition"] == "resolve-context-gaps"


@pytest.mark.django_db
def test_protects_guidance_published_in_an_operating_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    approve_operation,
) -> None:
    python_project(tmp_path)
    client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    deleted = client.delete(f"/api/records/{dependencies['record_id']}")
    approve_operation(client, deleted)
    deleted = client.delete(f"/api/records/{dependencies['record_id']}")

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert deleted.status_code == 422
    assert deleted.json() == {"detail": "A record published in an operating contract cannot be deleted."}
    assert response.status_code == 200
    assert response.json()["readiness"] == "ready"
    assert response.json()["receipt"]["diagnostics"] == []


@pytest.mark.django_db
def test_marks_stale_guidance_revision_incomplete(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    revised = client.put(
        f"/api/records/categories/{dependencies['category_id']}/content-schema",
        data={"content_schema": {"type": "object", "required": ["summary"]}},
        content_type="application/json",
    )

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert revised.status_code == 200
    assert response.status_code == 200
    assert response.json()["readiness"] == "incomplete"
    assert response.json()["guidance"][0]["schema_revision"] == 1
    assert response.json()["guidance"][0]["current_schema_revision"] == 2
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_revision_stale",
            "message": "Bound guidance uses an obsolete category schema revision. Review and republish it.",
            "guidance_ids": [dependencies["record_id"]],
        }
    ]


@pytest.mark.django_db
def test_health_reports_conflicting_guidance_authority(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first = client.put(
        f"/api/records/{dependencies['record_id']}",
        data={
            "title": "Project context",
            "content": {"authority": "project-policy"},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    second = client.post(
        "/api/records",
        data={
            "title": "Conflicting project context",
            "content": {"authority": "project-policy"},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [first["id"], second["id"]]
    registered = client.post("/api/projects", data=payload, content_type="application/json")
    assert registered.status_code == 201
    accept_health_architecture(client, tmp_path, registered.json())

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )
    resolution = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(tmp_path)},
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["readiness"] == "conflicted"
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_authority_conflict",
            "message": "Multiple bound guidance records claim authority 'project-policy'. Bind one effective source.",
            "guidance_ids": sorted([first["id"], second["id"]]),
        }
    ]
    assert health.json()["healthy"] is False
    assert [finding["rule"] for finding in health.json()["failures"]] == ["authority-conflict"]


@pytest.mark.django_db
def test_marks_changed_published_guidance_incomplete(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    second = client.post(
        "/api/records",
        data={
            "title": "Additional project context",
            "content": {},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [dependencies["record_id"], second["id"]]
    client.post("/api/projects", data=payload, content_type="application/json")
    changed = client.put(
        f"/api/records/{second['id']}",
        data={
            "title": "Changed project context",
            "content": {},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert changed.status_code == 200
    assert response.status_code == 200
    assert response.json()["readiness"] == "incomplete"
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_revision_changed",
            "message": "Published operating-contract guidance has changed. Publish a new contract revision.",
            "guidance_ids": [second["id"]],
        }
    ]


@pytest.mark.django_db
def test_updates_registered_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    project = created.json()["project"]

    update = {
        "title": "Renamed project",
        "stack": payload["discovery"]["stack"],
        "boundaries_yaml": payload["boundaries_yaml"],
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
        "scaffolding_id": payload["scaffolding_id"],
    }
    updated = client.put(
        f"/api/projects/{project['id']}",
        data=update,
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json() == {**project, "title": "Renamed project"}
    assert client.get(f"/api/projects/{project['id']}").json() == updated.json()
    configurations = client.get(f"/api/projects/{project['id']}/architecture-configurations")
    assert configurations.status_code == 200
    references = configurations.json()["items"]
    assert len(references) == 1
    assert references[0]["project_id"] == project["id"]
    configuration = client.get(f"/api/projects/{project['id']}/architecture-configurations/{references[0]['id']}")
    assert configuration.status_code == 200
    assert configuration.json() == {
        "id": references[0]["id"],
        "project_id": project["id"],
        "revision": references[0]["revision"],
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
        "boundaries_document": "boundaries_yaml",
        "shape_document": "shape_yaml",
        "boundaries_total_characters": len(BOUNDARIES_YAML),
        "shape_total_characters": len(UNHEALTHY_SHAPE_YAML),
    }


@pytest.mark.django_db
def test_reads_revision_pinned_architecture_configuration_content(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    project_id = resolution["project"]["id"]
    reference = client.get(f"/api/projects/{project_id}/architecture-configurations").json()["items"][0]

    response = client.get(
        f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
        data={
            "document": "boundaries_yaml",
            "expected_revision": reference["revision"],
            "offset": 0,
            "limit": 12,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": project_id,
        "configuration_id": reference["id"],
        "revision": reference["revision"],
        "document": "boundaries_yaml",
        "offset": 0,
        "limit": 12,
        "total_characters": len(BOUNDARIES_YAML),
        "content": BOUNDARIES_YAML[:12],
        "has_more": True,
        "next_offset": 12,
    }

    stale = client.get(
        f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
        data={
            "document": "boundaries_yaml",
            "expected_revision": "stale",
            "offset": 0,
            "limit": 12,
        },
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Architecture configuration changed; get it again before reading content."}

    invalid = client.get(
        f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
        data={
            "document": "boundaries_yaml",
            "expected_revision": reference["revision"],
            "offset": -1,
            "limit": 12,
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"][0]["loc"] == ["query", "offset"]
    assert invalid.json()["detail"][0]["ctx"] == {"ge": 0}


@pytest.mark.django_db
def test_generates_project_source_from_associated_scaffolding(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"files": ["generated/src/package/__init__.py"]}
    assert target.read_text(encoding="utf-8") == ""


@pytest.mark.django_db
def test_installs_agent_instructions_at_workspace_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "AGENTS.md"
    target.write_text("replace me\n", encoding="utf-8")

    response = client.put(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/agent-instructions"
    )

    assert response.status_code == 200
    assert response.json() == {"files": ["AGENTS.md"]}
    assert target.is_file()
    assert not target.is_symlink()
    installed = target.read_text(encoding="utf-8")
    assert "enclosure-mcp.get_workspace_context(root, task)" in installed
    assert "enclosure-mcp.check_project_health" in installed
    assert installed.endswith("\n")
    assert installed.rstrip("\n").count("\n") == 0


@pytest.mark.django_db
def test_generation_respects_create_if_missing(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    scaffolding = client.get(f"/api/scaffoldings/{dependencies['scaffolding_id']}").json()
    manifest = scaffolding["spec"]["templates"][0]
    content = client.get(
        f"/api/scaffoldings/{dependencies['scaffolding_id']}/template-content",
        data={
            "path": manifest["path"],
            "expected_revision": manifest["revision"],
            "offset": 0,
            "limit": 512,
        },
    )
    assert content.status_code == 200
    update = {
        "language_id": scaffolding["language_id"],
        "name": scaffolding["name"],
        "description": scaffolding["description"],
        "spec": {
            "language": scaffolding["spec"]["language"],
            "variables": scaffolding["spec"]["variables"],
            "templates": [
                {
                    "path": manifest["path"],
                    "content": content.json()["content"],
                    "write_mode": "create_if_missing",
                }
            ],
        },
    }
    updated = client.put(
        f"/api/scaffoldings/{dependencies['scaffolding_id']}",
        data=update,
        content_type="application/json",
    )
    assert updated.status_code == 200
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Destination already contains: generated/src/package/__init__.py"}
    assert target.read_text(encoding="utf-8") == "existing"


@pytest.mark.django_db
def test_generation_rejects_destination_outside_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": f"../{outside.name}", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Generation destination escapes the project root."}
    assert not outside.exists()


@pytest.mark.django_db
def test_get_project_returns_not_found(client: Client) -> None:
    response = client.get("/api/projects/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_update_project_returns_not_found(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)

    response = client.put(
        "/api/projects/missing",
        data={
            "title": "Missing project",
            "stack": discover(client, tmp_path)["stack"],
            "boundaries_yaml": BOUNDARIES_YAML,
            "shape_yaml": HEALTHY_SHAPE_YAML,
            "scaffolding_id": dependencies["scaffolding_id"],
        },
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


def test_siren_root_exposes_projects_collection(client: Client) -> None:
    response = client.get("/siren/", headers={"accept": "application/vnd.siren+json"})

    assert response.status_code == 200
    assert {link["href"] for link in response.json()["links"]} >= {
        "http://testserver/siren/projects",
    }


@pytest.mark.django_db
def test_registration_rejects_missing_scaffolding(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["scaffolding_id"] = "missing"

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_registration_rejects_missing_record(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = ["missing"]

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json() == {"detail": "Operating contract guidance must reference existing records."}


@pytest.mark.django_db
def test_registration_rejects_duplicate_record_bindings(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] *= 2

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json() == {"detail": "An operating contract revision cannot reference guidance more than once."}


@pytest.mark.django_db
def test_registration_rejects_duplicate_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201

    duplicate = client.post("/api/projects", data=payload, content_type="application/json")

    assert duplicate.status_code == 422
    assert duplicate.json() == {"detail": f"Workspace root is already bound: {tmp_path}"}


@pytest.mark.django_db
def test_failed_registration_does_not_reserve_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [dependencies["record_id"], "missing"]

    failed = client.post("/api/projects", data=payload, content_type="application/json")
    assert failed.status_code == 422

    payload["record_ids"] = [dependencies["record_id"]]
    retried = client.post("/api/projects", data=payload, content_type="application/json")

    assert retried.status_code == 201


@pytest.mark.django_db
def test_health_rejects_a_project_without_an_accepted_architecture_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Project health requires exactly one accepted project architecture contract."}


@pytest.mark.django_db
def test_health_blocks_closed_coverage_when_observer_support_is_incomplete(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution, coverage="closed")

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200, response.json()
    assert response.json()["healthy"] is False
    conformance = next(report for report in response.json()["reports"] if report["id"] == "architecture.conformance")
    coverage = {item["assertion_kind"]: item for item in conformance["coverage"]}
    assert coverage["member"]["unverified"] == 1
    assert coverage["relationship"]["unverified"] == 1
    coverage_findings = [
        finding
        for finding in response.json()["failures"]
        if finding["kind"] == "conformance" and finding["evidence"]["kind"] == "coverage"
    ]
    assert {finding["evidence"]["assertion_kind"] for finding in coverage_findings} == {
        "member",
        "relationship",
    }
    assert {finding["target"] for finding in coverage_findings} == {"architecture-contract-unit:application"}


@pytest.mark.django_db
def test_health_reports_a_missing_declared_artifact(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    (tmp_path / "src" / "example" / "models.py").unlink()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200, response.json()
    assert response.json()["healthy"] is False
    finding = next(
        finding
        for finding in response.json()["failures"]
        if finding["rule"] == "architecture.conformance.artifact" and finding["target"] == "artifact:models"
    )
    assert finding["finding_kind"] == "missing"
    assert finding["owner"] == "implementation"
    assert finding["expected"]["fields"] == {
        "path": "src/example/models.py",
        "artifact_kind": "file",
    }
    assert finding["observed"] == []


@pytest.mark.django_db
def test_health_closed_coverage_reports_an_unexpected_empty_directory(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution, coverage="closed")
    (tmp_path / "src" / "example" / "empty").mkdir()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200, response.json()
    assert response.json()["healthy"] is False
    finding = next(
        finding
        for finding in response.json()["failures"]
        if finding["rule"] == "architecture.conformance.artifact"
        and finding["finding_kind"] == "unexpected"
        and finding["observed"][0]["fields"]["path"] == "src/example/empty"
    )
    assert finding["owner"] == "implementation"
    assert finding["observed"][0]["fields"]["artifact_kind"] == "directory"


@pytest.mark.django_db
def test_health_closed_coverage_preserves_an_internal_symlink_path(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution, coverage="closed")
    (tmp_path / "src" / "example" / "alias.py").symlink_to("service.py")

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200, response.json()
    assert response.json()["healthy"] is False
    finding = next(
        finding
        for finding in response.json()["failures"]
        if finding["rule"] == "architecture.conformance.artifact"
        and finding["finding_kind"] == "unexpected"
        and finding["observed"][0]["fields"]["path"] == "src/example/alias.py"
    )
    assert finding["observed"][0]["fields"]["artifact_kind"] == "file"


@pytest.mark.django_db
def test_health_rejects_an_artifact_symlink_that_escapes_the_workspace(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution, coverage="closed")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("class OutsideWorkspace:\n    pass\n", encoding="utf-8")
    (tmp_path / "src" / "example" / "escape.py").symlink_to(outside)

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Architecture artifact path escapes the workspace: 'src/example/escape.py'."}


@pytest.mark.django_db(transaction=True)
def test_health_rejects_source_drift_before_returning_a_completed_report(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "DriftApplication")
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    caplog.clear()
    with ThreadPoolExecutor(max_workers=1) as executor:
        active_request = executor.submit(Client().get, path)
        guidance_deadline = monotonic() + 15
        while not any(
            cast(dict[str, object], record.msg).get("event") == "project_health_guidance_started"
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ):
            if active_request.done():
                pytest.fail("Health evaluation completed before source mutation could start.")
            if monotonic() >= guidance_deadline:
                pytest.fail("Health evaluation did not reach guidance verification.")
            sleep(0.001)
        replacement = tmp_path / ".app.py.replacement"
        replacement.write_text("class ChangedApplication:\n    pass\n", encoding="utf-8")
        os.replace(replacement, tmp_path / "app.py")
        response = active_request.result(timeout=5)

    assert response.status_code == 422
    assert response.json() == {"detail": "Project source changed during health evaluation."}


@pytest.mark.django_db
def test_health_returns_typed_conformance_evidence_for_mismatched_code(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    (tmp_path / "src" / "example" / "service.py").write_text(
        "class ExampleService:\n"
        "    value: str\n\n"
        "    def execute(self, request: int) -> str:\n"
        "        return str(request)\n",
        encoding="utf-8",
    )

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200, response.json()
    assert response.json()["healthy"] is False
    finding = next(
        finding
        for finding in response.json()["failures"]
        if finding["kind"] == "conformance" and finding["rule"] == "architecture.conformance.member"
    )
    assert finding["finding_kind"] == "mismatched"
    assert finding["state"] == "fail"
    assert finding["owner"] == "implementation"
    assert finding["evidence"]["kind"] == "assertion"
    assert finding["evidence"]["diagram_evidence"]
    assert finding["evidence"]["implementation_evidence_ids"]
    assert finding["expected"]["kind"] == "member"
    assert finding["expected"]["fields"]["parameters"][0]["type"]["name"] == "String"
    assert finding["observed"][0]["kind"] == "member"
    assert finding["observed"][0]["fields"]["parameters"][0]["type"]["name"] == "Integer"
    assert len(finding["fingerprint"]) == 64


@pytest.mark.django_db
def test_health_returns_a_complete_attestation_for_an_aligned_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()
    accept_health_architecture(client, tmp_path, resolution)

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["outcome"] == "healthy"
    assert response.json()["reports"]
    assert all(report["failure_count"] == 0 for report in response.json()["reports"])
    conformance = next(report for report in response.json()["reports"] if report["id"] == "architecture.conformance")
    assert {item["assertion_kind"] for item in conformance["coverage"]} == {
        "artifact",
        "classifier",
        "entity",
        "entity_field",
        "member",
        "relationship",
    }
    assert sum(item["passed"] for item in conformance["coverage"]) > 0
    assert all(item["failed"] == 0 and item["unverified"] == 0 for item in conformance["coverage"])
    attestation = response.json()["attestation"]
    assert attestation["digest_algorithm"] == "sha256"
    assert [component["kind"] for component in attestation["components"]] == [
        "contract",
        "implementation_evidence",
        "realization",
        "policies",
        "configuration",
        "schemas",
        "tools",
        "comparator",
        "findings",
    ]
    assert all(len(component["digest"]) == 64 for component in attestation["components"])
    assert len(attestation["digest"]) == 64
    assert len(response.json()["revision"]) == 64

    stale = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-attestation",
        data={"expected_revision": "stale"},
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Project health changed; check it again before requesting the attestation."}

    exact = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-attestation",
        data={"expected_revision": response.json()["revision"]},
    )
    assert exact.status_code == 200
    assert exact.json() == attestation
    guidance_report = next(report for report in response.json()["reports"] if report["id"] == "guidance-graph")
    assert guidance_report["advisory_count"] == 0


@pytest.mark.django_db
def test_health_reports_malformed_guidance_graph_and_blocks_ready_context(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    supplemental = client.post(
        "/api/records",
        data={
            "title": "Python refinement",
            "content": {"authority": "unrelated:python", "guidance": ["Keep typing strict."]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    outside = client.post(
        "/api/records",
        data={
            "title": "Outside guidance",
            "content": {"guidance": ["This record is not effective for the project."]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    project = resolution["project"]
    workspace = resolution["workspace"]
    scoped = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [supplemental["id"]]},
        content_type="application/json",
    )
    relationships = client.put(
        f"/api/projects/{project['id']}/guidance-relationships",
        data={
            "relationships": [
                {
                    "source_record_id": dependencies["record_id"],
                    "target_record_id": supplemental["id"],
                    "kind": "refinement",
                },
                {
                    "source_record_id": supplemental["id"],
                    "target_record_id": dependencies["record_id"],
                    "kind": "prerequisite",
                },
                {
                    "source_record_id": dependencies["record_id"],
                    "target_record_id": outside["id"],
                    "kind": "containment",
                },
            ]
        },
        content_type="application/json",
    )

    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change Python typing"},
        content_type="application/json",
    )

    assert scoped.status_code == 200
    assert relationships.status_code == 200
    assert all(relationship["id"] for relationship in relationships.json())
    assert {relationship["project_id"] for relationship in relationships.json()} == {project["id"]}
    assert client.get(f"/api/projects/{project['id']}/guidance-relationships").json()["items"] == relationships.json()
    assert health.status_code == 200
    assert health.json()["healthy"] is False
    rules = {finding["rule"] for finding in health.json()["failures"]}
    assert {
        "ambiguous-entry-point",
        "dangling-relationship",
        "guidance-cycle",
        "invalid-refinement",
    } <= rules
    assert all(finding["related_ids"] for finding in health.json()["failures"])
    assert all(finding["remediation"] for finding in health.json()["failures"])
    assert context.status_code == 200
    assert context.json()["readiness"] == "incomplete"
    assert "guidance-cycle" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}


@pytest.mark.django_db
def test_health_keeps_unreachable_oversized_optional_guidance_advisory(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    optional = client.post(
        "/api/records",
        data={
            "title": "Large optional guidance",
            "content": {"summary": "x" * 5000},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    project = resolution["project"]
    workspace = resolution["workspace"]
    client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [optional["id"]]},
        content_type="application/json",
    )

    response = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["failures"] == []
    assert {finding["rule"] for finding in response.json()["advisories"]} == {
        "optional-budget-exceeded",
        "unreachable-guidance",
    }


@pytest.mark.django_db
def test_health_blocks_oversized_required_guidance(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    client.put(
        f"/api/records/{dependencies['record_id']}",
        data={
            "title": "Project context",
            "content": {"guidance": ["x" * 9000]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    project = resolution["project"]
    workspace = resolution["workspace"]

    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert health.json()["healthy"] is False
    assert [finding["rule"] for finding in health.json()["failures"]] == ["guidance-oversized"]
    assert context.json()["readiness"] == "incomplete"
    assert "guidance-oversized" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}


@pytest.mark.django_db
def test_health_fails_when_architecture_has_a_shape_violation(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(
        discover(client, tmp_path),
        dependencies,
        shape_yaml=UNHEALTHY_SHAPE_YAML,
    )
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()
    accept_health_architecture(client, tmp_path, resolution)

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200
    assert response.json()["healthy"] is False
    assert response.json()["failure_count"] > 0
    assert response.json()["revision"]
    assert response.json()["failure_kind"] == "failure"
    assert response.json()["advisory_kind"] == "advisory"
    finding = next(finding for finding in response.json()["failures"] if finding["rule"] == "max_classes_per_file")
    assert finding == {
        "kind": "shape",
        "rule": "max_classes_per_file",
        "target": "app.py",
        "message": "file reports 1; configured limit is 0 in realm 'project'.",
        "next_action": "Review file in app.py: max_classes_per_file is 1; configured limit is 0.",
        "source_file": "app.py",
        "realm": "project",
        "symbol_kind": "file",
        "symbol_name": "",
        "actual": 1,
        "limit": 0,
    }
    page = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-findings",
        data={
            "kind": response.json()["failure_kind"],
            "expected_revision": response.json()["revision"],
            "offset": 0,
            "limit": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["revision"] == response.json()["revision"]
    assert page.json()["kind"] == "failure"
    assert page.json()["total"] == response.json()["failure_count"]
    assert len(page.json()["items"]) == 1

    stale = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-findings",
        data={"kind": "failure", "expected_revision": "stale", "offset": 0, "limit": 1},
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Project health changed; check it again before requesting findings."}


@pytest.mark.django_db
def test_health_preserves_exact_dependency_flow_location(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "example_tool.py").write_text(
        "from src.example_module import example_value\n",
        encoding="utf-8",
    )
    source = tmp_path / "src"
    source.mkdir()
    (source / "__init__.py").write_text("", encoding="utf-8")
    module = source / "example_module"
    module.mkdir(parents=True)
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "example_value.py").write_text("EXAMPLE_VALUE = 1\n", encoding="utf-8")
    payload = registration(discover(client, tmp_path), dependencies)
    payload["boundaries_yaml"] = FLOW_BOUNDARIES_YAML
    resolution = client.post("/api/projects", data=payload, content_type="application/json").json()
    accept_health_architecture(client, tmp_path, resolution)

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200
    finding = next(
        finding
        for finding in response.json()["failures"]
        if finding["kind"] == "flow" and finding["target"] == "example_tool.py"
    )
    assert finding == {
        "kind": "flow",
        "rule": "boundary:unclassified",
        "target": "example_tool.py",
        "message": "tracked file does not match an architecture module",
        "next_action": ("Review dependency location example_tool.py at path index 0 against boundary:unclassified."),
        "violation_type": "module-boundaries",
        "path": ["example_tool.py"],
        "violation_index": 0,
        "source_module": "",
        "target_module": "",
    }


@override_settings(PROJECT_HEALTH_MAX_CONCURRENCY=1)
@pytest.mark.django_db(transaction=True)
def test_health_rejects_excess_concurrency_and_recovers_capacity(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    source = BlockingArchitectureSource.create(tmp_path)
    source.replace()
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    assert client.get(path).status_code == 200
    source.block()
    with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=2):
        with ThreadPoolExecutor(max_workers=1) as executor:
            active_request = executor.submit(Client().get, path)
            writer = asyncio.run(asyncio.wait_for(source.connect_writer_when_ready(), timeout=5))
            try:
                started = monotonic()
                unavailable = client.get(path)
                unavailable_duration = monotonic() - started
                bounded = active_request.result(timeout=5)
            finally:
                os.close(writer)

    source.replace()
    recovery_started = monotonic()
    with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=15):
        recovered = client.get(path)
    recovery_duration = monotonic() - recovery_started

    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "Project health execution capacity is exhausted."}
    assert unavailable_duration < 1
    assert bounded.status_code == 504
    assert recovered.status_code == 200
    assert recovery_duration < 15


@override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=1)
@pytest.mark.django_db(transaction=True)
def test_health_times_out_blocked_work_and_recovers_capacity(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = BlockingArchitectureSource.create(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    caplog.clear()
    started = monotonic()
    timed_out = client.get(path)
    timeout_duration = monotonic() - started
    source.replace()
    with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=15):
        recovered = client.get(path)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    completed_run_id = next(
        event["run_id"]
        for event in events
        if event.get("event") == "project_health_terminal" and event["outcome"] == "completed"
    )
    replacement = next(
        event
        for event in events
        if event.get("event") == "project_health_worker_bootstrap_terminal" and event["run_id"] == completed_run_id
    )

    assert timed_out.status_code == 504
    assert timed_out.json() == {"detail": "Project health execution timed out."}
    assert 1 <= timeout_duration < 3
    assert recovered.status_code == 200
    assert replacement["replacement"] is True


@pytest.mark.django_db(transaction=True)
def test_health_disconnect_cancels_work_and_recovers(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    source = BlockingArchitectureSource.create(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    first_request = DisconnectingHealthRequest(
        application=ApplicationFactory().build(),
        path=path,
        source=source,
    )

    second_request = DisconnectingHealthRequest(
        application=ApplicationFactory().build(),
        path=path,
        source=source,
    )
    asyncio.run(first_request.run_before(second_request))
    recovered = client.get(path)
    terminal_events = [
        json.loads(line) for line in capfd.readouterr().err.splitlines() if '"event": "project_health_terminal"' in line
    ]
    canceled_events = [event for event in terminal_events if event["outcome"] == "canceled"]

    assert first_request.messages == []
    assert second_request.messages == []
    assert recovered.status_code == 200
    assert [event["outcome"] for event in terminal_events] == ["canceled", "canceled", "completed"]
    assert len(canceled_events) == 2


@pytest.mark.django_db(transaction=True)
def test_health_recovers_from_corrupted_persistent_cache(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
    existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "CorruptCacheApplication")
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    baseline = client.get(path)
    entries = tuple(
        entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
    )
    completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
    completed_entry.write_bytes(b"{")

    caplog.clear()
    recovered = client.get(path)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]

    assert baseline.status_code == 200, baseline.json()
    assert recovered.status_code == 200, recovered.json()
    assert recovered.json() == baseline.json()
    assert any(
        event.get("event") == "project_health_phase_terminal" and event.get("cache_outcome") == "corrupt"
        for event in events
    )
    assert any(
        event.get("event") == "project_health_phase_terminal"
        and event.get("phase") == "final-input-verification"
        and event.get("outcome") == "completed"
        for event in events
    )


@pytest.mark.django_db(transaction=True)
def test_health_recovers_from_stale_persistent_cache(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
    existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "StaleCacheApplication")
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    baseline = client.get(path)
    entries = tuple(
        entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
    )
    completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
    other_entry = next(entry for entry in entries if entry.parent.name != "completed-result")
    completed_payload = completed_entry.read_bytes()
    completed_entry.write_bytes(other_entry.read_bytes())
    other_entry.write_bytes(completed_payload)

    caplog.clear()
    recovered = client.get(path)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]

    assert baseline.status_code == 200, baseline.json()
    assert recovered.status_code == 200, recovered.json()
    assert recovered.json() == baseline.json()
    assert any(
        event.get("event") == "project_health_phase_terminal" and event.get("cache_outcome") == "stale"
        for event in events
    )
    assert any(
        event.get("event") == "project_health_phase_terminal"
        and event.get("phase") == "final-input-verification"
        and event.get("outcome") == "completed"
        for event in events
    )


@pytest.mark.django_db
def test_health_reuses_exact_stage_caches_after_configuration_change(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "StageCacheApplication")
    payload = registration(discover(client, tmp_path), dependencies)
    resolution = client.post(
        "/api/projects",
        data=payload,
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    caplog.clear()
    cold = client.get(path)
    warm = client.get(path)
    updated = client.put(
        f"/api/projects/{resolution['project']['id']}",
        data={
            "title": resolution["project"]["title"],
            "stack": payload["discovery"]["stack"],
            "boundaries_yaml": payload["boundaries_yaml"],
            "shape_yaml": """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 2
""",
            "scaffolding_id": payload["scaffolding_id"],
        },
        content_type="application/json",
    )
    changed = client.get(path)

    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    terminal_events = [event for event in events if event.get("event") == "project_health_terminal"]
    cold_run_id, warm_run_id, changed_run_id = (event["run_id"] for event in terminal_events)
    cold_phases = [
        event
        for event in events
        if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == cold_run_id
    ]
    warm_phases = [
        event
        for event in events
        if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == warm_run_id
    ]
    changed_phases = [
        event
        for event in events
        if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == changed_run_id
    ]

    assert cold.status_code == 200, cold.json()
    assert warm.status_code == 200, warm.json()
    assert updated.status_code == 200, updated.json()
    assert changed.status_code == 200, changed.json()
    assert cold.json()["healthy"] is True
    assert warm.json() == cold.json()
    assert changed.json()["healthy"] is True
    assert sum(event["phase"] == "modwire-code-map" for event in cold_phases) == 1
    assert any(event["phase"] == "completed-result-cache" and event["cache_outcome"] == "hit" for event in warm_phases)
    assert all(event["phase"] != "modwire-code-map" for event in warm_phases)
    assert any(
        event["phase"] == "implementation-manifest"
        and event["outcome"] == "cache-lookup"
        and event["cache_outcome"] == "hit"
        for event in changed_phases
    )
    assert any(
        event["phase"] == "modwire-reports" and event["outcome"] == "cache-lookup" and event["cache_outcome"] == "miss"
        for event in changed_phases
    )
    assert all(
        any(
            event["phase"] == phase and event["outcome"] == "cache-lookup" and event["cache_outcome"] == "hit"
            for event in changed_phases
        )
        for phase in ("evidence", "realization", "comparison")
    )
    assert any(
        event["phase"] == "attestation" and event["outcome"] == "cache-lookup" and event["cache_outcome"] == "miss"
        for event in changed_phases
    )


@pytest.mark.django_db
def test_health_is_insensitive_to_one_hundred_thousand_excluded_files(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    record_property: Callable[[str, object], None],
) -> None:
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "ScaleApplication")
    payload = registration(discover(client, tmp_path), dependencies, shape_yaml=COMPLETE_SHAPE_YAML)
    payload["boundaries_yaml"] = COMPLETE_BOUNDARIES_YAML
    resolution = client.post(
        "/api/projects",
        data=payload,
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    baseline = client.get(path)
    noise = tmp_path / ".dev" / "noise"
    creation_started = monotonic()
    for directory_index in range(100):
        directory = noise / str(directory_index)
        directory.mkdir(parents=True)
        for file_index in range(1000):
            (directory / str(file_index)).touch()
    creation_duration = monotonic() - creation_started

    caplog.clear()
    started = monotonic()
    repeated = client.get(path)
    duration = monotonic() - started
    record_property("file_creation_seconds", creation_duration)
    record_property("health_seconds", duration)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]

    assert baseline.status_code == 200, baseline.json()
    assert repeated.status_code == 200, repeated.json()
    assert repeated.json() == baseline.json()
    assert duration < 5
    assert any(
        event.get("event") == "project_health_phase_terminal"
        and event.get("phase") == "completed-result-cache"
        and event.get("cache_outcome") == "hit"
        for event in events
    )
    assert all(
        event.get("phase") != "modwire-code-map"
        for event in events
        if event.get("event") == "project_health_phase_terminal"
    )


@pytest.mark.django_db
def test_repeated_health_reuses_warm_execution_and_observes_source_changes(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    caplog.clear()
    healthy = client.get(path)
    (tmp_path / "app.py").write_text(
        "class ExampleApplication:\n    pass\n\nclass ExampleHandler:\n    pass\n",
        encoding="utf-8",
    )
    changed = client.get(path)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    terminal_events = [event for event in events if event.get("event") == "project_health_terminal"]
    changed_run_id = terminal_events[-1]["run_id"]
    changed_worker_events = [
        event["event"]
        for event in events
        if event.get("run_id") == changed_run_id
        and event.get("event") in {"project_health_worker_started", "project_health_worker_reused"}
    ]

    assert healthy.status_code == 200
    assert healthy.json()["healthy"] is True
    assert changed.status_code == 200
    assert changed.json()["healthy"] is False
    assert "max_classes_per_file" in {finding["rule"] for finding in changed.json()["failures"]}
    assert changed_worker_events == ["project_health_worker_reused"]


@pytest.mark.django_db(transaction=True)
def test_health_remains_truthful_when_persistent_cache_is_unavailable(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
    existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "UnavailableCacheApplication")
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"

    baseline = client.get(path)
    entries = tuple(
        entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
    )
    completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
    completed_payload = completed_entry.read_bytes()
    completed_entry.unlink()
    completed_entry.mkdir()
    caplog.clear()
    try:
        first = client.get(path)
        second = client.get(path)
    finally:
        completed_entry.rmdir()
        completed_entry.write_bytes(completed_payload)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    completed_run_ids = {
        event["run_id"]
        for event in events
        if event.get("event") == "project_health_terminal" and event.get("outcome") == "completed"
    }

    assert baseline.status_code == 200, baseline.json()
    assert first.status_code == 200, first.json()
    assert second.status_code == 200, second.json()
    assert first.json() == baseline.json()
    assert second.json() == baseline.json()
    assert len(completed_run_ids) == 2
    assert all(
        any(
            event.get("run_id") == run_id
            and event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "cache-persistence"
            and event.get("cache_outcome") == "unavailable"
            for event in events
        )
        for run_id in completed_run_ids
    )
    assert all(
        all(
            event.get("phase") != "modwire-code-map"
            for event in events
            if event.get("run_id") == run_id and event.get("event") == "project_health_phase_terminal"
        )
        for run_id in completed_run_ids
    )


@pytest.mark.django_db
def test_health_cold_execution_is_stable_across_five_independent_projects(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    record_property: Callable[[str, object], None],
) -> None:
    responses = []
    durations = []
    caplog.clear()
    for index in range(5):
        root = tmp_path / str(index)
        root.mkdir()
        python_project(root)
        distinguish_project_source(root, "ColdApplication")
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, root), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, root, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )
        started = monotonic()
        responses.append(client.get(path))
        durations.append(monotonic() - started)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    completed_run_ids = {
        event["run_id"]
        for event in events
        if event.get("event") == "project_health_terminal" and event.get("outcome") == "completed"
    }
    record_property("cold_durations_seconds", ",".join(str(duration) for duration in durations))
    record_property("cold_max_seconds", max(durations))

    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["healthy"] is True for response in responses)
    assert all(response.json()["failures"] == [] for response in responses)
    assert len({tuple(report["id"] for report in response.json()["reports"]) for response in responses}) == 1
    assert max(durations) < 5
    assert len(completed_run_ids) == 5
    assert all(
        any(
            event.get("run_id") == run_id
            and event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "completed-result-cache"
            and event.get("cache_outcome") == "miss"
            for event in events
        )
        for run_id in completed_run_ids
    )
    assert all(
        sum(
            event.get("run_id") == run_id
            and event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "modwire-code-map"
            for event in events
        )
        == 1
        for run_id in completed_run_ids
    )


@pytest.mark.django_db
def test_health_warm_execution_is_stable_across_twenty_requests(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    record_property: Callable[[str, object], None],
) -> None:
    python_project(tmp_path)
    distinguish_project_source(tmp_path, "WarmApplication")
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    accept_health_architecture(client, tmp_path, resolution)
    path = f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    baseline = client.get(path)

    caplog.clear()
    responses = []
    durations = []
    for _ in range(20):
        started = monotonic()
        responses.append(client.get(path))
        durations.append(monotonic() - started)
    ordered_durations = sorted(durations)
    events = [
        cast(dict[str, object], record.msg)
        for record in caplog.records
        if record.name.startswith("enclosure.projects.services.health")
    ]
    completed_run_ids = {
        event["run_id"]
        for event in events
        if event.get("event") == "project_health_terminal" and event.get("outcome") == "completed"
    }
    record_property("warm_durations_seconds", ",".join(str(duration) for duration in ordered_durations))
    record_property("warm_p95_seconds", ordered_durations[18])
    record_property("warm_max_seconds", max(ordered_durations))

    assert baseline.status_code == 200, baseline.json()
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json() == baseline.json() for response in responses)
    assert ordered_durations[18] < 1
    assert max(ordered_durations) < 5
    assert len(completed_run_ids) == 20
    assert all(
        any(
            event.get("run_id") == run_id
            and event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "completed-result-cache"
            and event.get("cache_outcome") == "hit"
            for event in events
        )
        for run_id in completed_run_ids
    )
    assert all(
        event.get("phase") != "modwire-code-map"
        for event in events
        if event.get("event") == "project_health_phase_terminal"
    )


@pytest.mark.django_db
def test_insights_contains_only_non_gating_reports(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights"
    )

    assert response.status_code == 200
    assert response.json()["reports"]
    assert response.json()["report_count"] == len(response.json()["reports"])
    assert response.json()["sections"]
    assert all("metadata" in report for report in response.json()["reports"])

    section = response.json()["sections"][0]
    page = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={
            "path": section["path"],
            "expected_revision": response.json()["revision"],
            "offset": 0,
            "limit": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["project_id"] == resolution["project"]["id"]
    assert page.json()["workspace_id"] == resolution["workspace"]["id"]
    assert page.json()["revision"] == response.json()["revision"]
    assert page.json()["path"] == section["path"]
    assert page.json()["total"] == section["total"]
    assert len(page.json()["items"]) == 1

    stale = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={"path": section["path"], "expected_revision": "stale", "offset": 0, "limit": 1},
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Project insights changed; read them again before requesting a page."}

    oversized = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={
            "path": section["path"],
            "expected_revision": response.json()["revision"],
            "offset": 0,
            "limit": 26,
        },
    )
    assert oversized.status_code == 422
    assert oversized.json()["detail"][0]["loc"] == ["query", "limit"]
    assert oversized.json()["detail"][0]["ctx"] == {"le": 25}

    content_path = (
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/content"
    )
    section_offset = 0
    item_offset = 0
    recovered: dict[str, list[object]] = {}
    while True:
        content = client.get(
            content_path,
            data={
                "expected_revision": response.json()["revision"],
                "section_offset": section_offset,
                "item_offset": item_offset,
                "limit": 1,
            },
        )
        assert content.status_code == 200
        recovered.setdefault(content.json()["path"], []).extend(content.json()["items"])
        if not content.json()["has_more"]:
            break
        section_offset = content.json()["next_section_offset"]
        item_offset = content.json()["next_item_offset"]

    assert set(recovered) == {section["path"] for section in response.json()["sections"]}
    assert {path: len(items) for path, items in recovered.items()} == {
        section["path"]: section["total"] for section in response.json()["sections"]
    }

    stale_content = client.get(
        content_path,
        data={"expected_revision": "stale", "section_offset": 0, "item_offset": 0, "limit": 1},
    )
    assert stale_content.status_code == 422
    assert stale_content.json() == {"detail": "Project insights changed; read them again before requesting content."}


@pytest.mark.django_db
@pytest.mark.parametrize("report", ["health-violations", "insights"])
def test_reports_return_not_found_for_missing_project(client: Client, report: str) -> None:
    response = client.get(f"/api/projects/missing/workspaces/missing-workspace/{report}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/projects/discoveries", {}),
        ("/api/projects", {}),
        ("/api/projects", {"discovery": {"root": "/tmp", "stack": {}}}),
    ],
)
def test_project_commands_reject_structurally_invalid_payloads(
    client: Client,
    path: str,
    payload: dict,
) -> None:
    response = client.post(path, data=payload, content_type="application/json")

    assert response.status_code == 422


@pytest.mark.django_db
def test_project_collections_are_deterministically_paginated(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    projects = []
    for index in range(3):
        root = tmp_path / f"project-{index}"
        root.mkdir()
        python_project(root)
        created = client.post(
            "/api/projects",
            data=registration(discover(client, root), dependencies),
            content_type="application/json",
        )
        assert created.status_code == 201
        projects.append(created.json()["project"])
    project = projects[0]
    for index in range(2):
        root = tmp_path / f"worktree-{index}"
        root.mkdir()
        python_project(root)
        bound = client.post(
            f"/api/projects/{project['id']}/workspaces",
            data={"root": str(root), "architecture_root": str(root)},
            content_type="application/json",
        )
        assert bound.status_code == 201
    records = [dependencies["record_id"]]
    for index in range(3):
        record = client.post(
            "/api/records",
            data={
                "title": f"Pagination guidance {index}",
                "content": {},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        assert record.status_code == 201
        records.append(record.json()["id"])
    scopes = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": records[1:]},
        content_type="application/json",
    )
    relationships = client.put(
        f"/api/projects/{project['id']}/guidance-relationships",
        data={
            "relationships": [
                {
                    "source_record_id": source,
                    "target_record_id": target,
                    "kind": "containment",
                }
                for source, target in zip(records[:3], records[1:], strict=True)
            ]
        },
        content_type="application/json",
    )
    assert scopes.status_code == 200
    assert relationships.status_code == 200

    three_item_paths = (
        "/api/projects",
        f"/api/projects/{project['id']}/workspaces",
        f"/api/projects/{project['id']}/guidance-scopes",
        f"/api/projects/{project['id']}/guidance-relationships",
    )
    for path in three_item_paths:
        first = client.get(path, {"offset": 0, "limit": 1})
        intermediate = client.get(path, {"offset": 1, "limit": 1})
        final = client.get(path, {"offset": 2, "limit": 1})
        empty = client.get(path, {"offset": 3, "limit": 1})

        assert first.status_code == 200
        assert len(first.json()["items"]) == 1
        assert first.json()["has_more"] is True
        assert first.json()["next_offset"] == 1
        assert first.json()["limit"] == 1
        assert intermediate.status_code == 200
        assert len(intermediate.json()["items"]) == 1
        assert intermediate.json()["has_more"] is True
        assert intermediate.json()["next_offset"] == 2
        assert intermediate.json()["limit"] == 1
        assert final.status_code == 200
        assert len(final.json()["items"]) == 1
        assert final.json()["has_more"] is False
        assert final.json()["next_offset"] == 3
        assert final.json()["limit"] == 1
        assert empty.status_code == 200
        assert empty.json() == {
            "items": [],
            "has_more": False,
            "next_offset": 3,
            "limit": 1,
        }

    configuration_path = f"/api/projects/{project['id']}/architecture-configurations"
    configuration = client.get(configuration_path, {"offset": 0, "limit": 1})
    empty_configuration = client.get(configuration_path, {"offset": 1, "limit": 1})

    assert configuration.status_code == 200
    assert len(configuration.json()["items"]) == 1
    assert configuration.json()["has_more"] is False
    assert configuration.json()["next_offset"] == 1
    assert configuration.json()["limit"] == 1
    assert empty_configuration.status_code == 200
    assert empty_configuration.json() == {
        "items": [],
        "has_more": False,
        "next_offset": 1,
        "limit": 1,
    }


def test_sirenity_owns_project_collection_continuation_links() -> None:
    schema = Client().get("/api/openapi.json").json()
    paths = (
        "/api/projects",
        "/api/projects/{project_id}/workspaces",
        "/api/projects/{project_id}/guidance-scopes",
        "/api/projects/{project_id}/guidance-relationships",
        "/api/projects/{project_id}/architecture-configurations",
    )

    for path in paths:
        operation = schema["paths"][path]["get"]
        links = operation["responses"]["200"]["links"]
        assert links["next"]["operationId"] == operation["operationId"]
        assert links["next"]["parameters"] == {
            "offset": "$response.body#/next_offset",
            "limit": "$response.body#/limit",
        }
        if "{project_id}" in path:
            assert links["next"]["x-sirenity"]["sourceInputs"] == {"project_id": "$request.path.project_id"}
        item_links = [link for name, link in links.items() if name != "next"]
        assert item_links
        assert all(link["x-sirenity"]["itemCollection"] == "$response.body#/items" for link in item_links)


def test_project_bounded_page_schemas_publish_current_limits() -> None:
    schema = Client().get("/api/openapi.json").json()
    operations = {
        "/api/projects/{project_id}/architecture-configurations/{configuration_id}/content": {
            "offset": {"minimum": 0},
            "limit": {"minimum": 0},
        },
        "/api/projects/{project_id}/workspaces/{workspace_id}/insights/pages": {
            "offset": {"minimum": 0},
            "limit": {"minimum": 1, "maximum": 25},
        },
        "/api/projects/{project_id}/workspaces/{workspace_id}/health-findings": {
            "offset": {"minimum": 0},
            "limit": {"minimum": 0},
        },
        "/api/projects/{project_id}/workspaces/{workspace_id}/insights/content": {
            "section_offset": {"minimum": 0},
            "item_offset": {"minimum": 0},
            "limit": {"minimum": 0},
        },
    }

    for path, expected_bounds in operations.items():
        parameters = {
            parameter["name"]: parameter["schema"]
            for parameter in schema["paths"][path]["get"]["parameters"]
            if parameter["in"] == "query"
        }
        for name, bounds in expected_bounds.items():
            assert {key: parameters[name][key] for key in bounds} == bounds


@pytest.mark.django_db
def test_project_collection_pagination_is_bounded(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    response = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    assert response.status_code == 201
    project_id = response.json()["project"]["id"]
    paths = (
        "/api/projects",
        f"/api/projects/{project_id}/workspaces",
        f"/api/projects/{project_id}/guidance-scopes",
        f"/api/projects/{project_id}/guidance-relationships",
        f"/api/projects/{project_id}/architecture-configurations",
    )

    for path in paths:
        assert client.get(path, {"offset": -1, "limit": 10}).status_code == 422
        assert client.get(path, {"offset": 0, "limit": 101}).status_code == 422
