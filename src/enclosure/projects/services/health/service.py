from dataclasses import dataclass

from wireup import injectable

from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from ..registry.model import ArchitectureConfiguration, Project
from ..reports.model import HealthReport
from ..reports.service import ReportsService
from ..workspaces.model import WorkspaceBinding
from .validation import GuidanceHealthService


@injectable
@dataclass(frozen=True)
class ProjectHealthService:
    architecture: ReportsService
    guidance: GuidanceHealthService

    def check(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        configuration: ArchitectureConfiguration,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
    ) -> HealthReport:
        architecture = self.architecture.generate_health_report(
            workspace.architecture_root,
            project.language_id,
            configuration.boundaries_yaml,
            configuration.shape_yaml,
        )
        guidance = self.guidance.check(project.id, binding)
        return HealthReport(
            healthy=architecture.healthy and guidance.healthy,
            reports=(*architecture.reports, guidance.model_dump(mode="json")),
        )
