from dataclasses import dataclass
from pathlib import Path

from django.test import Client
from modwire.application import ModwireApplication, ScanPolicy

from .projects import discover, python_project, registration


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
