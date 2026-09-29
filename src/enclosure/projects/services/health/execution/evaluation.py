from dataclasses import dataclass, field

from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext

from ...architecture_manifests.evidence.model import ImplementationContext
from ...architecture_manifests.model import ArchitectureComparisonConclusion
from ...architecture_manifests.service import ArchitectureManifestService
from ...reports.adapters.architecture import ArchitectureAdapter
from ..attestations.identity import ArchitectureConformanceIdentity
from ..attestations.model import ArchitectureAttestationContext, ArchitectureFindingAttestationEvidence
from ..attestations.service import ArchitectureAttestationService
from ..conformance.service import ArchitectureConformanceService
from .model import CompletedHealthExecutionResult, HealthExecutionRequest


@injectable
@dataclass(frozen=True)
class HealthWorkerEvaluationService:
    architecture: ArchitectureAdapter
    manifests: ArchitectureManifestService
    conformance: ArchitectureConformanceService
    attestations: ArchitectureAttestationService
    cache: CacheDiagnosticsContext
    identity: ArchitectureConformanceIdentity = field(default_factory=ArchitectureConformanceIdentity, init=False)

    def evaluate(self, request: HealthExecutionRequest) -> CompletedHealthExecutionResult:
        self.cache.begin()
        try:
            observation = self.architecture.observe(request.source)
            reports = tuple(report for report in observation.reports if "violations" in report)
            bundle = self.manifests.evaluate(
                request.contract.manifest,
                ImplementationContext(
                    implementation_document=observation.implementation_document,
                    artifact_paths=observation.artifact_paths,
                ),
            )
            conformance = self.conformance.project(bundle.comparison)
            attestation = self.attestations.attest(
                ArchitectureAttestationContext(
                    contract=request.contract.manifest,
                    implementation=bundle.implementation,
                    realization=bundle.realization,
                    comparison=bundle.comparison,
                    findings=tuple(
                        ArchitectureFindingAttestationEvidence(
                            fingerprint=finding.fingerprint,
                            owner=finding.owner,
                            kind=finding.finding_kind,
                            message=finding.message,
                            next_action=finding.next_action,
                        )
                        for finding in conformance.findings
                    ),
                    operating_contract=request.contract.operating_contract,
                    update_policy=request.contract.update_policy,
                    configuration_revision=request.contract.configuration_revision,
                    identity=self.identity.model_copy(update={"comparison": self.manifests.comparator.identity}),
                )
            )
            return CompletedHealthExecutionResult(
                healthy=(
                    all(not report["violations"] for report in reports)
                    and conformance.conclusion == ArchitectureComparisonConclusion.CONFORMS
                ),
                reports=reports,
                conformance=conformance,
                attestation=attestation,
                cache_outcomes=self.cache.read(),
                detail="",
            )
        finally:
            self.cache.reset()
