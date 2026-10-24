import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256

from django.apps import apps
from django.test import Client
from mermaiden import Application


@dataclass(frozen=True)
class ArchivedArchitectureApplication:
    client: Client
    project_id: str
    publication_id: str

    @property
    def publication_url(self) -> str:
        return f"/api/projects/{self.project_id}/architecture-contract-publications/{self.publication_id}"

    @property
    def manifest_url(self) -> str:
        return f"{self.publication_url}/manifest"


@dataclass(frozen=True)
class ArchivedArchitectureApplicationFactory:
    client: Client

    def create(self, snapshot_version: int, registry_fingerprint: str) -> ArchivedArchitectureApplication:
        project_model = apps.get_model("projects", "Project")
        publication_model = apps.get_model("projects", "ArchitectureContractPublication")
        unit_model = apps.get_model("projects", "ArchitectureContractUnit")
        diagram_model = apps.get_model("projects", "ArchitectureContractDiagram")
        project = project_model.objects.create(
            title="Example archived architecture",
            language_id="python",
            language_version="3.14",
            package_manager_id="uv",
            scaffolding_id="example-scaffolding",
        )
        publication = publication_model.objects.create(
            project=project,
            version=1,
            authority=f"project:{project.pk}:architecture-contract",
            revision="a" * 64,
        )
        unit = unit_model.objects.create(
            publication=publication,
            key="example-application",
            diagram_set_id="example-diagrams",
            source_root="src/example",
            coverage="declared",
            position=0,
        )
        with Application.create() as application:
            specifications = (
                (
                    "treeView-beta",
                    "tree",
                    "complete",
                    (
                        {"operation": "add_directory", "arguments": {"id": "example-source", "label": "src"}},
                        {
                            "operation": "add_directory",
                            "arguments": {"id": "example-package", "label": "example"},
                        },
                        {"operation": "add_file", "arguments": {"id": "example-file", "label": "service.py"}},
                        {
                            "operation": "add_branch",
                            "arguments": {
                                "id": "example-source-package",
                                "parent_id": "example-source",
                                "child_id": "example-package",
                            },
                        },
                        {
                            "operation": "add_branch",
                            "arguments": {
                                "id": "example-package-file",
                                "parent_id": "example-package",
                                "child_id": "example-file",
                            },
                        },
                    ),
                ),
                (
                    "classDiagram",
                    "uml",
                    "focused",
                    (
                        {
                            "operation": "add_class",
                            "arguments": {
                                "id": "src/example/service.py::class:src/example/service.ExampleService",
                                "label": "ExampleService",
                            },
                        },
                    ),
                ),
                (
                    "erDiagram",
                    "entity",
                    "complete",
                    (
                        {
                            "operation": "add_entity",
                            "arguments": {"id": "example-record", "label": "EXAMPLE_RECORD"},
                        },
                    ),
                ),
            )
            for position, (kind, role, scope, commands) in enumerate(specifications):
                diagram = application.create_diagram(kind)
                application.apply_batch(diagram, commands)
                snapshot = application.snapshot(diagram).to_dict()
                snapshot["version"] = snapshot_version
                snapshot["configuration"]["fields"] = self.configuration_fields(kind)
                canonical = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                diagram_model.objects.create(
                    unit=unit,
                    diagram_id=f"example-{role}",
                    diagram_revision=1,
                    role=role,
                    scope=scope,
                    kind=kind,
                    snapshot_version=snapshot_version,
                    registry_fingerprint=registry_fingerprint,
                    snapshot_digest=sha256(canonical.encode("utf-8")).hexdigest(),
                    snapshot=snapshot,
                    position=position,
                )
        return ArchivedArchitectureApplication(
            client=self.client,
            project_id=str(project.pk),
            publication_id=str(publication.pk),
        )

    def remove_draft_evidence(self, architecture: ArchivedArchitectureApplication) -> None:
        diagram_model = apps.get_model("projects", "ArchitectureContractDiagram")
        diagram = diagram_model.objects.filter(unit__publication_id=architecture.publication_id).order_by("position")[0]
        snapshot = deepcopy(diagram.snapshot)
        del snapshot["draft"]
        diagram.snapshot = snapshot
        diagram.save(update_fields=("snapshot",))

    def configuration_fields(self, kind: str) -> dict[str, object]:
        if kind != "erDiagram":
            return {"wrap": True}
        return {
            "wrap": True,
            "title_top_margin": 25,
            "diagram_padding": 20,
            "layout_direction": "TB",
            "min_entity_width": 100,
            "min_entity_height": 75,
            "entity_padding": 15,
            "stroke": "gray",
            "fill": "honeydew",
            "use_max_width": True,
        }
