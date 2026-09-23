from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar

import structlog
from wireup import injectable

from ...errors import ProjectHealthCanceled, ProjectHealthTimedOut
from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from ..registry.model import ArchitectureConfiguration, Project
from ..reports.model import ArchitectureSource, HealthReport, HealthReportSet
from ..reports.service import ReportsService
from ..workspaces.model import WorkspaceBinding
from .execution import HealthExecutionService, HealthRunOutcome
from .validation import GuidanceHealthService


@injectable
@dataclass(frozen=True)
class ProjectHealthService:
    logger: ClassVar = structlog.get_logger(__name__)

    execution: HealthExecutionService
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
        outcome = HealthRunOutcome.FAILED
        self.logger.info(
            "project_health_started",
            started_ns=started_ns,
            project_id=project.id,
            workspace_id=workspace.id,
        )
        try:
            architecture = self.execution.execute(
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
            report = self.reports.summarize_health_report(
                HealthReportSet(
                    healthy=architecture.healthy and guidance.healthy,
                    reports=(*architecture.reports, guidance.model_dump(mode="json")),
                )
            )
            outcome = HealthRunOutcome.COMPLETED
            return report
        except ProjectHealthCanceled:
            outcome = HealthRunOutcome.CANCELED
            raise
        except ProjectHealthTimedOut:
            outcome = HealthRunOutcome.TIMED_OUT
            raise
        finally:
            finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_terminal",
                outcome=outcome.value,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                project_id=project.id,
                workspace_id=workspace.id,
            )
