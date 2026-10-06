from dataclasses import dataclass
from typing import ClassVar

import structlog
from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext
from enclosure.shared.execution import RequestCancellationContext

from ....errors import ProjectHealthCanceled, ProjectHealthExecutionFailed, ProjectHealthTimedOut, ProjectsError
from ...reports.model import ArchitectureSource
from ..conformance.model import ArchitectureHealthContract, ArchitectureHealthResult
from .gateway import HealthWorkerGateway
from .model import HealthExecutionRequest, HealthRunOutcome


@injectable
@dataclass(frozen=True)
class HealthExecutionService:
    logger: ClassVar = structlog.get_logger(__name__)

    worker: HealthWorkerGateway
    cancellation: RequestCancellationContext
    cache: CacheDiagnosticsContext

    def execute(
        self,
        run_id: str,
        source: ArchitectureSource,
        contract: ArchitectureHealthContract,
    ) -> ArchitectureHealthResult:
        result = self.worker.execute(
            HealthExecutionRequest(run_id=run_id, source=source, contract=contract),
            self.cancellation.current(),
            self.worker.timeout_seconds,
        )
        for diagnostic in result.phase_diagnostics:
            self.logger.info(
                "project_health_phase_terminal",
                run_id=run_id,
                phase=diagnostic.phase.value,
                outcome=diagnostic.outcome,
                duration_ns=diagnostic.duration_ns,
                item_count=diagnostic.item_count,
                cache_outcome=diagnostic.cache_outcome.value,
            )
        self.cache.record(result.cache_outcomes)
        if result.outcome == HealthRunOutcome.COMPLETED:
            return ArchitectureHealthResult(
                healthy=result.healthy,
                reports=result.reports,
                conformance=result.conformance,
                attestation=result.attestation,
                input_identity=result.input_identity,
            )
        if result.outcome == HealthRunOutcome.CANCELED:
            raise ProjectHealthCanceled(result.detail)
        if result.outcome == HealthRunOutcome.TIMED_OUT:
            raise ProjectHealthTimedOut(result.detail)
        if result.outcome == HealthRunOutcome.REJECTED:
            raise ProjectsError(result.detail)
        raise ProjectHealthExecutionFailed(result.detail)
