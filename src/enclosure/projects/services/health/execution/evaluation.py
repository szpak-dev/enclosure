from dataclasses import dataclass

from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext

from ...architecture_manifests.model import ArchitectureComparisonConclusion
from ...reports.adapters.architecture import ArchitectureAdapter
from ..conformance.service import ArchitectureConformanceService
from .model import CompletedHealthExecutionResult, HealthExecutionRequest


@injectable
@dataclass(frozen=True)
class HealthWorkerEvaluationService:
    architecture: ArchitectureAdapter
    conformance: ArchitectureConformanceService
    cache: CacheDiagnosticsContext

    def evaluate(self, request: HealthExecutionRequest) -> CompletedHealthExecutionResult:
        self.cache.begin()
        try:
            observation = self.architecture.observe(request.source)
            reports = tuple(report for report in observation.reports if "violations" in report)
            conformance = self.conformance.evaluate(request.contract, observation)
            return CompletedHealthExecutionResult(
                healthy=(
                    all(not report["violations"] for report in reports)
                    and conformance.report.conclusion == ArchitectureComparisonConclusion.CONFORMS
                ),
                reports=reports,
                conformance=conformance.report,
                attestation=conformance.attestation,
                cache_outcomes=self.cache.read(),
                detail="",
            )
        finally:
            self.cache.reset()
