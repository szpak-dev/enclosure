from dataclasses import dataclass
from time import perf_counter_ns

import structlog
from wireup import injectable

from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from ..registry.model import ArchitectureConfiguration, Project
from ..reports.model import ArchitectureSource, HealthReport, HealthReportSet
from ..reports.service import ReportsService
from ..workspaces.model import WorkspaceBinding
from .validation import GuidanceHealthService

logger = structlog.get_logger(__name__)


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
        started_ns = perf_counter_ns()
        logger.info(
            "project_health_started",
            started_ns=started_ns,
            project_id=project.id,
            workspace_id=workspace.id,
        )
        try:
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
        finally:
            finished_ns = perf_counter_ns()
            logger.info(
                "project_health_finished",
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                project_id=project.id,
                workspace_id=workspace.id,
            )
