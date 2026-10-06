from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar
from uuid import uuid4

import structlog
from wireup import injectable

from ...errors import ProjectHealthCanceled, ProjectHealthTimedOut, ProjectsError
from ..contracts.model import ConfiguredOperatingContractBinding
from ..registry.model import ArchitectureConfiguration, Project
from ..reports.model import ArchitectureSource, HealthReport, HealthReportSet
from ..reports.service import ReportsService
from ..workspaces.model import WorkspaceBinding
from .conformance.contract import ArchitectureHealthContractService
from .execution.model import HealthRunOutcome
from .execution.service import HealthExecutionService
from .input_identity import ArchitectureHealthInputIdentityService
from .validation import GuidanceHealthService


@injectable
@dataclass(frozen=True)
class ProjectHealthService:
    logger: ClassVar = structlog.get_logger(__name__)

    execution: HealthExecutionService
    reports: ReportsService
    guidance: GuidanceHealthService
    contracts: ArchitectureHealthContractService
    input_identity: ArchitectureHealthInputIdentityService

    def check(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        configuration: ArchitectureConfiguration,
        binding: ConfiguredOperatingContractBinding,
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
            contract = self.contracts.resolve(project.id, binding, configuration)
            source = ArchitectureSource(
                project_id=project.id,
                workspace_id=workspace.id,
                architecture_root=workspace.architecture_root,
                language=project.language_id,
                boundaries_yaml=configuration.boundaries_yaml,
                shape_yaml=configuration.shape_yaml,
            )
            architecture = self.execution.execute(
                run_id,
                source,
                contract,
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
                        conformance=architecture.conformance,
                        attestation=architecture.attestation,
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
            verification_started_ns = perf_counter_ns()
            verification_outcome = "failed"
            try:
                self.input_identity.verify(
                    project,
                    workspace,
                    configuration,
                    binding,
                    source,
                    contract.manifest,
                    architecture.input_identity,
                    architecture.attestation.source_digest,
                )
                verification_outcome = "completed"
            finally:
                verification_finished_ns = perf_counter_ns()
                self.logger.info(
                    "project_health_phase_terminal",
                    run_id=run_id,
                    phase="final-input-verification",
                    outcome=verification_outcome,
                    started_ns=verification_started_ns,
                    finished_ns=verification_finished_ns,
                    duration_ns=verification_finished_ns - verification_started_ns,
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
        except ProjectsError:
            outcome = HealthRunOutcome.REJECTED
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
