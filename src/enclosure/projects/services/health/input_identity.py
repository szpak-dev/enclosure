from dataclasses import dataclass
from typing import cast

from wireup import injectable

from ...errors import ProjectsError
from ..contracts.model import ConfiguredOperatingContractBinding
from ..contracts.service import OperatingContractsService
from ..registry.model import ArchitectureConfiguration, Project
from ..registry.service import RegistryService
from ..reports.adapters.architecture import ArchitectureAdapter
from ..reports.model import ArchitectureSource
from ..workspaces.model import WorkspaceBinding
from ..workspaces.service import WorkspaceService


@injectable
@dataclass(frozen=True)
class ArchitectureHealthInputIdentityService:
    registry: RegistryService
    workspaces: WorkspaceService
    contracts: OperatingContractsService
    architecture: ArchitectureAdapter

    def verify(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        configuration: ArchitectureConfiguration,
        binding: ConfiguredOperatingContractBinding,
        source: ArchitectureSource,
        expected_source_digest: str,
    ) -> None:
        self.architecture.verify_source_identity(source, expected_source_digest)
        current_project = self.registry.get(project.id)
        current_workspace = self.workspaces.get(project.id, workspace.id)
        current_configuration = self.registry.get_current_architecture_configuration(project.id)
        current_binding = self.contracts.get_binding(project.id)
        if current_binding.state == "unconfigured":
            raise ProjectsError("Project health inputs changed during evaluation.")
        if (
            current_project.language_id != project.language_id
            or current_workspace.architecture_root != workspace.architecture_root
            or current_configuration != configuration
            or cast(ConfiguredOperatingContractBinding, current_binding) != binding
        ):
            raise ProjectsError("Project health inputs changed during evaluation.")
