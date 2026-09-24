from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar
from uuid import uuid4

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
        run_id = uuid4().hex
        started_ns = perf_counter_ns()
        outcome = HealthRunOutcome.FAILED
        self.logger.info(
            "project_health_started",
            run_id=run_id,
            started_ns=started_ns,
            project_id=project.id,
            workspace_id=workspace.id,
        )
        try:
            architecture = self.execution.execute(
                run_id,
                ArchitectureSource(
                    project_id=project.id,
                    workspace_id=workspace.id,
                    architecture_root=workspace.architecture_root,
                    language=project.language_id,
                    boundaries_yaml=configuration.boundaries_yaml,
                    shape_yaml=configuration.shape_yaml,
                ),
            )
            guidance_started_ns = perf_counter_ns()
            self.logger.info(
                "project_health_guidance_started",
                run_id=run_id,
                started_ns=guidance_started_ns,
                project_id=project.id,
                workspace_id=workspace.id,
            )
            try:
                guidance = self.guidance.check(project.id, binding)
            finally:
                guidance_finished_ns = perf_counter_ns()
                self.logger.info(
                    "project_health_guidance_terminal",
                    run_id=run_id,
                    started_ns=guidance_started_ns,
                    finished_ns=guidance_finished_ns,
                    duration_ns=guidance_finished_ns - guidance_started_ns,
                    project_id=project.id,
                    workspace_id=workspace.id,
                )
            summarization_started_ns = perf_counter_ns()
            self.logger.info(
                "project_health_summarization_started",
                run_id=run_id,
                started_ns=summarization_started_ns,
                project_id=project.id,
                workspace_id=workspace.id,
            )
            try:
                report = self.reports.summarize_health_report(
                    HealthReportSet(
                        healthy=architecture.healthy and guidance.healthy,
                        reports=(*architecture.reports, guidance.model_dump(mode="json")),
                    )
                )
            finally:
                summarization_finished_ns = perf_counter_ns()
                self.logger.info(
                    "project_health_summarization_terminal",
                    run_id=run_id,
                    started_ns=summarization_started_ns,
                    finished_ns=summarization_finished_ns,
                    duration_ns=summarization_finished_ns - summarization_started_ns,
                    project_id=project.id,
                    workspace_id=workspace.id,
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
                run_id=run_id,
                outcome=outcome.value,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                project_id=project.id,
                workspace_id=workspace.id,
            )
