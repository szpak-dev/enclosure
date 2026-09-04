from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from django.db import transaction
from pydantic import JsonValue
from wireup import injectable

from ..errors import ProjectsError
from .adapters import ScaffoldingsAdapter
from .context.model import WorkspaceContext
from .context.service import WorkspaceContextService
from .contracts.model import (
    ConfiguredOperatingContractBinding,
    OperatingContract,
    OperatingContractReference,
    OperatingContractRevision,
    UnconfiguredOperatingContractBinding,
)
from .contracts.service import OperatingContractsService
from .generation import GenerationResult, GenerationService
from .health.graph import GuidanceGraphService
from .health.model import GuidanceRelationship, GuidanceRelationshipInput
from .health.service import ProjectHealthService
from .registry.model import ArchitectureConfiguration, Project
from .registry.service import RegistryService
from .reports import HealthReport, InsightsReport, ReportsService
from .reports.adapters import ArchitectureAdapter
from .routing.model import GuidanceScope
from .routing.service import WorkspaceRoutingService
from .stack import DetectedStack, DiscoveredProject, StackDetector
from .workspaces import (
    WorkspaceBinding,
    WorkspaceLocation,
    WorkspaceResolution,
    WorkspaceService,
    WorkspaceStatus,
)


@injectable
@dataclass(frozen=True)
class ProjectsService:
    architecture: ArchitectureAdapter
    contracts: OperatingContractsService
    context: WorkspaceContextService
    generation: GenerationService
    graph: GuidanceGraphService
    health: ProjectHealthService
    scaffoldings: ScaffoldingsAdapter
    stack: StackDetector
    reports: ReportsService
    registry: RegistryService
    routing: WorkspaceRoutingService
    workspaces: WorkspaceService

    def discover_project(self, root: str) -> DiscoveredProject:
        stack = self.stack.detect(root)
        return DiscoveredProject(root=root, stack=stack)

    def find_all_projects(self) -> tuple[Project, ...]:
        return self.registry.find_all()

    def find_project_by_root(self, root: str) -> Project:
        return self.resolve_workspace(root).project

    def resolve_workspace(self, root: str) -> WorkspaceResolution:
        return self.workspaces.resolve(root)

    def get_project(self, project_id: str) -> Project:
        return self.registry.get(project_id)

    def find_project_architecture_configurations(
        self,
        project_id: str,
    ) -> tuple[ArchitectureConfiguration, ...]:
        return self.registry.find_architecture_configurations(project_id)

    def get_project_architecture_configuration(
        self,
        project_id: str,
        configuration_id: str,
    ) -> ArchitectureConfiguration:
        return self.registry.get_architecture_configuration(project_id, configuration_id)

    def find_workspaces(self, project_id: str) -> tuple[WorkspaceBinding, ...]:
        return self.workspaces.find(project_id)

    def get_workspace(self, project_id: str, workspace_id: str) -> WorkspaceBinding:
        return self.workspaces.get(project_id, workspace_id)

    def bind_workspace(self, project_id: str, root: str, architecture_root: str) -> WorkspaceBinding:
        return self.workspaces.bind(
            project_id,
            WorkspaceLocation(root=root, architecture_root=architecture_root),
        )

    def replace_workspace(
        self,
        project_id: str,
        workspace_id: str,
        root: str,
        architecture_root: str,
        expected_revision: int,
    ) -> WorkspaceBinding:
        return self.workspaces.replace(
            project_id,
            workspace_id,
            WorkspaceLocation(root=root, architecture_root=architecture_root),
            expected_revision,
        )

    def inspect_workspace(self, project_id: str, workspace_id: str) -> WorkspaceStatus:
        return self.workspaces.inspect(project_id, workspace_id)

    def delete_workspace(self, project_id: str, workspace_id: str, expected_revision: int) -> None:
        self.workspaces.delete(project_id, workspace_id, expected_revision)

    def get_workspace_context(self, root: str, task: str) -> WorkspaceContext:
        resolution = self.resolve_workspace(root)
        return self.context.resolve(
            resolution.project.id,
            resolution.workspace.root,
            self.contracts.get_binding(resolution.project.id),
            task,
        )

    def find_guidance_scopes(self, project_id: str) -> tuple[GuidanceScope, ...]:
        self.registry.get(project_id)
        return self.routing.find_scopes(project_id)

    def replace_guidance_scopes(
        self,
        project_id: str,
        record_ids: tuple[str, ...],
    ) -> tuple[GuidanceScope, ...]:
        self.registry.get(project_id)
        return self.routing.replace_scopes(project_id, record_ids)

    def find_guidance_relationships(self, project_id: str) -> tuple[GuidanceRelationship, ...]:
        self.registry.get(project_id)
        return self.graph.find_relationships(project_id)

    def replace_guidance_relationships(
        self,
        project_id: str,
        relationships: tuple[Mapping[str, str], ...],
    ) -> tuple[GuidanceRelationship, ...]:
        self.registry.get(project_id)
        return self.graph.replace_relationships(
            project_id,
            tuple(GuidanceRelationshipInput.model_validate(relationship) for relationship in relationships),
        )

    def create_operating_contract(self, title: str, authority: str, provenance: str) -> OperatingContract:
        return self.contracts.create(title, authority, provenance)

    def get_operating_contract(self, contract_id: str) -> OperatingContract:
        return self.contracts.get(contract_id)

    def publish_operating_contract_revision(
        self,
        contract_id: str,
        record_ids: tuple[str, ...],
        references: tuple[Mapping[str, str], ...],
    ) -> OperatingContractRevision:
        return self.contracts.publish(
            contract_id,
            record_ids,
            tuple(OperatingContractReference.model_validate(reference) for reference in references),
        )

    def get_operating_contract_revision(self, contract_id: str, version: int) -> OperatingContractRevision:
        return self.contracts.get_revision(contract_id, version)

    def bind_project_operating_contract(
        self,
        project_id: str,
        contract_id: str,
        version: int,
        update_policy: Literal["pinned", "follow-latest"],
    ) -> ConfiguredOperatingContractBinding:
        self.registry.get(project_id)
        return self.contracts.bind(project_id, contract_id, version, update_policy)

    def replace_project_operating_contract_binding(
        self,
        project_id: str,
        contract_id: str,
        version: int,
        update_policy: Literal["pinned", "follow-latest"],
    ) -> ConfiguredOperatingContractBinding:
        self.registry.get(project_id)
        return self.contracts.replace_binding(project_id, contract_id, version, update_policy)

    def get_project_operating_contract_binding(
        self,
        project_id: str,
    ) -> ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding:
        self.registry.get(project_id)
        return self.contracts.get_binding(project_id)

    def generate_source(
        self,
        project_id: str,
        workspace_id: str,
        destination: str,
        parameters: dict[str, JsonValue],
    ) -> GenerationResult:
        return self.generation.generate(
            self.registry.get(project_id),
            self.workspaces.get(project_id, workspace_id),
            destination,
            parameters,
        )

    @transaction.atomic
    def register_project(
        self,
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
        record_ids: list[str],
    ) -> WorkspaceResolution:
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id)
        project = self.registry.register(
            self._project_data(self._project_title(discovery.root), discovery.stack, scaffolding_id),
            boundaries_yaml,
            shape_yaml,
        )
        workspace = self.workspaces.bind(
            project.id,
            WorkspaceLocation(root=discovery.root, architecture_root=architecture_root),
        )
        self.contracts.bootstrap(project.id, tuple(record_ids))
        return WorkspaceResolution(project=project, workspace=workspace)

    def update_project(
        self,
        project_id: str,
        title: str,
        stack: DetectedStack,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
    ) -> Project:
        normalized_title = self._validate_title(title)
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id)
        return self.registry.update(
            project_id,
            self._project_data(normalized_title, stack, scaffolding_id),
            boundaries_yaml,
            shape_yaml,
        )

    def check_health(self, project_id: str, workspace_id: str) -> HealthReport:
        configuration = self.registry.get_current_architecture_configuration(project_id)
        project = self.registry.get(project_id)
        return self.health.check(
            project,
            self.workspaces.get(project_id, workspace_id),
            configuration,
            self.contracts.get_binding(project_id),
        )

    def read_insights(self, project_id: str, workspace_id: str) -> InsightsReport:
        configuration = self.registry.get_current_architecture_configuration(project_id)
        project = self.registry.get(project_id)
        workspace = self.workspaces.get(project_id, workspace_id)
        return self.reports.generate_insights_report(
            workspace.architecture_root,
            project.language_id,
            configuration.boundaries_yaml,
            configuration.shape_yaml,
        )

    def _validate_project(
        self,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
    ) -> None:
        self.scaffoldings.check_scaffolding_existence(scaffolding_id)
        self.architecture.validate_yaml_config(boundaries_yaml, shape_yaml)

    def _project_data(
        self,
        title: str,
        stack: DetectedStack,
        scaffolding_id: str,
    ) -> dict[str, str]:
        return {
            "title": title,
            "language_id": stack.language,
            "language_version": stack.language_version,
            "package_manager_id": stack.package_manager,
            "scaffolding_id": scaffolding_id,
        }

    def _project_title(self, root: str) -> str:
        return self._validate_title(Path(root).expanduser().resolve().name)

    def _validate_title(self, title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ProjectsError("Project title is required.")
        if len(normalized) > 255:
            raise ProjectsError("Project title must not exceed 255 characters.")
        return normalized
