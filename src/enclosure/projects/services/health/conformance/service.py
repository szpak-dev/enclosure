from collections.abc import Sequence
from dataclasses import dataclass, field
from operator import attrgetter

from wireup import injectable

from ....errors import ProjectsError
from ...adapters.modwire import ModwireManifestAdapter
from ...architecture_manifests.comparator import ArchitectureContractComparator
from ...architecture_manifests.facts.model import ArchitectureFactCapability
from ...architecture_manifests.model import ArchitectureComparisonState
from ...reports.model import ArchitectureObservation
from ..attestations.identity import ArchitectureConformanceIdentity
from ..attestations.model import ArchitectureAttestationContext
from ..attestations.service import ArchitectureAttestationService
from .model import (
    ArchitectureConformanceCoverage,
    ArchitectureConformanceEvaluation,
    ArchitectureConformanceFinding,
    ArchitectureConformanceReport,
    ArchitectureHealthContract,
)
from .projectors.base import ArchitectureConformanceFindingProjector


@injectable
@dataclass(frozen=True)
class ArchitectureConformanceService:
    comparator: ArchitectureContractComparator
    modwire: ModwireManifestAdapter
    attestations: ArchitectureAttestationService
    projectors: Sequence[ArchitectureConformanceFindingProjector]
    identity: ArchitectureConformanceIdentity = field(default_factory=ArchitectureConformanceIdentity, init=False)

    def evaluate(
        self,
        contract: ArchitectureHealthContract,
        observation: ArchitectureObservation,
    ) -> ArchitectureConformanceEvaluation:
        observed = self.modwire.read(observation.implementation_document)
        comparison = self.comparator.compare(contract.manifest, observed)
        projectors = tuple(sorted(self.projectors, key=attrgetter("order", "name")))
        findings: list[ArchitectureConformanceFinding] = []
        for result in comparison.results:
            if result.state == ArchitectureComparisonState.PASS:
                continue
            matches = tuple(projector for projector in projectors if projector.supports(result))
            if len(matches) != 1:
                raise ProjectsError(
                    f"Architecture assertion {result.assertion_id!r} has no unique health finding projector."
                )
            findings.append(matches[0].project(result, contract.manifest, observed))
        coverage = tuple(
            ArchitectureConformanceCoverage(
                capability=capability,
                passed=sum(
                    result.capability == capability and result.state == ArchitectureComparisonState.PASS
                    for result in comparison.results
                ),
                failed=sum(
                    result.capability == capability and result.state == ArchitectureComparisonState.FAIL
                    for result in comparison.results
                ),
                unverified=sum(
                    result.capability == capability and result.state == ArchitectureComparisonState.UNVERIFIED
                    for result in comparison.results
                ),
            )
            for capability in ArchitectureFactCapability
        )
        report = ArchitectureConformanceReport(
            id="architecture.conformance",
            title="Architecture conformance",
            conclusion=comparison.conclusion,
            coverage=coverage,
            findings=tuple(findings),
            comparison_digest=comparison.digest,
        )
        attestation = self.attestations.attest(
            ArchitectureAttestationContext(
                contract=contract.manifest,
                observed=observed,
                comparison=comparison,
                operating_contract=contract.operating_contract,
                update_policy=contract.update_policy,
                configuration_revision=contract.configuration_revision,
                identity=self.identity.model_copy(update={"comparison": self.comparator.identity}),
            )
        )
        return ArchitectureConformanceEvaluation(report=report, attestation=attestation)
