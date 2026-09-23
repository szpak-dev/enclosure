from dataclasses import dataclass

from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext
from enclosure.shared.execution import RequestCancellationContext

from ....errors import ProjectHealthCanceled, ProjectHealthExecutionFailed, ProjectHealthTimedOut
from ...reports.model import ArchitectureSource, HealthReportSet
from .gateway import HealthWorkerGateway
from .model import HealthRunOutcome


@injectable
@dataclass(frozen=True)
class HealthExecutionService:
    worker: HealthWorkerGateway
    cancellation: RequestCancellationContext
    cache: CacheDiagnosticsContext

    def execute(self, source: ArchitectureSource) -> HealthReportSet:
        result = self.worker.execute(
            source,
            self.cancellation.current(),
            self.worker.timeout_seconds,
        )
        self.cache.record(result.cache_outcomes)
        match result.outcome:
            case HealthRunOutcome.COMPLETED:
                return HealthReportSet(
                    healthy=all(not report["violations"] for report in result.reports),
                    reports=result.reports,
                )
            case HealthRunOutcome.CANCELED:
                raise ProjectHealthCanceled(result.detail)
            case HealthRunOutcome.TIMED_OUT:
                raise ProjectHealthTimedOut(result.detail)
            case HealthRunOutcome.FAILED:
                raise ProjectHealthExecutionFailed(result.detail)
