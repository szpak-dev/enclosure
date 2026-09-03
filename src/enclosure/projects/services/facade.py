from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from django.db import transaction
from pydantic import JsonValue
from wireup import injectable

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
from .stack import DiscoveredProject, StackDetector


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

    def discover_project(self, root: str) -> DiscoveredProject:
        stack = self.stack.detect(root)
        return DiscoveredProject(root=root, stack=stack)

    def find_all_projects(self) -> tuple[Project, ...]:
        return self.registry.find_all()

    def find_project_by_root(self, root: str) -> Project:
        return self.registry.get_by_root(root)

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

    def get_workspace_context(self, root: str, task: str) -> WorkspaceContext:
        project = self.registry.get_by_root(root)
        return self.context.resolve(
            project.id,
            project.root,
            self.contracts.get_binding(project.id),
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
        destination: str,
        parameters: dict[str, JsonValue],
    ) -> GenerationResult:
        return self.generation.generate(project_id, destination, parameters)

    @transaction.atomic
    def register_project(
        self,
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
        record_ids: list[str],
    ) -> Project:
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id)
        project = self.registry.register(
            self._project_data(
                discovery,
                architecture_root,
                scaffolding_id,
            ),
            boundaries_yaml,
            shape_yaml,
        )
        self.contracts.bootstrap(project.id, tuple(record_ids))
        return project

    def update_project(
        self,
        project_id: str,
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
    ) -> Project:
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id)
        return self.registry.update(
            project_id,
            self._project_data(
                discovery,
                architecture_root,
                scaffolding_id,
            ),
            boundaries_yaml,
            shape_yaml,
        )

    def check_health(self, project_id: str) -> HealthReport:
        configuration = self.registry.get_current_architecture_configuration(project_id)
        project = self.registry.get(project_id)
        return self.health.check(
            project,
            configuration,
            self.contracts.get_binding(project_id),
        )

    def read_insights(self, project_id: str) -> InsightsReport:
        configuration = self.registry.get_current_architecture_configuration(project_id)
        project = self.registry.get(project_id)
        return self.reports.generate_insights_report(
            project.architecture_root,
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
        discovery: DiscoveredProject,
        architecture_root: str,
        scaffolding_id: str,
    ) -> dict[str, str]:
        return {
            "root": discovery.root,
            "architecture_root": architecture_root,
            "language_id": discovery.stack.language,
            "language_version": discovery.stack.language_version,
            "package_manager_id": discovery.stack.package_manager,
            "scaffolding_id": scaffolding_id,
        }
