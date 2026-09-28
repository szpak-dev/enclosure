from dataclasses import dataclass

from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext
from enclosure.shared.execution import RequestCancellationContext

from ....errors import ProjectHealthCanceled, ProjectHealthExecutionFailed, ProjectHealthTimedOut
from ...reports.model import ArchitectureSource
from ..conformance.model import ArchitectureHealthContract, ArchitectureHealthResult
from .gateway import HealthWorkerGateway
from .model import HealthExecutionRequest, HealthRunOutcome


@injectable
@dataclass(frozen=True)
class HealthExecutionService:
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
        self.cache.record(result.cache_outcomes)
        if result.outcome == HealthRunOutcome.COMPLETED:
            return ArchitectureHealthResult(
                healthy=result.healthy,
                reports=result.reports,
                conformance=result.conformance,
                attestation=result.attestation,
            )
        if result.outcome == HealthRunOutcome.CANCELED:
            raise ProjectHealthCanceled(result.detail)
        if result.outcome == HealthRunOutcome.TIMED_OUT:
            raise ProjectHealthTimedOut(result.detail)
        raise ProjectHealthExecutionFailed(result.detail)
