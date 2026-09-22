from dataclasses import dataclass

from wireup import injectable

from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from ..registry.model import ArchitectureConfiguration, Project
from ..reports.model import ArchitectureSource, HealthReport, HealthReportSet
from ..reports.service import ReportsService
from ..workspaces.model import WorkspaceBinding
from .validation import GuidanceHealthService


@injectable
@dataclass(frozen=True)
class ProjectHealthService:
    reports: ReportsService
    guidance: GuidanceHealthService

    def check(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        configuration: ArchitectureConfiguration,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
    ) -> HealthReport:
        architecture = self.reports.generate_health_report(
            ArchitectureSource(
                project_id=project.id,
                workspace_id=workspace.id,
                architecture_root=workspace.architecture_root,
                language=project.language_id,
                boundaries_yaml=configuration.boundaries_yaml,
                shape_yaml=configuration.shape_yaml,
            )
        )
        guidance = self.guidance.check(project.id, binding)
        return self.reports.summarize_health_report(
            HealthReportSet(
                healthy=architecture.healthy and guidance.healthy,
                reports=(*architecture.reports, guidance.model_dump(mode="json")),
            )
        )
