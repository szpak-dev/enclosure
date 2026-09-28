from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ....architecture_manifests.model import (
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureAssertionUnverified,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
)
from ....architecture_manifests.observed.model import ObservedImplementationManifest
from ..model import ArchitectureConformanceFinding, ArchitectureCoverageEvidence
from .base import ArchitectureConformanceFindingProjector


@injectable(as_type=ArchitectureConformanceFindingProjector, qualifier="architecture-coverage-finding")
@dataclass(frozen=True)
class ArchitectureCoverageFindingProjector(ArchitectureConformanceFindingProjector):
    name: str = field(default="coverage", init=False)
    order: int = field(default=30, init=False)

    def supports(self, result: ArchitectureAssertionResult) -> bool:
        return (
            result.state == ArchitectureComparisonState.UNVERIFIED
            and result.scope == ArchitectureAssertionScope.COVERAGE
        )

    def project(
        self,
        result: ArchitectureAssertionResult,
        contract: ArchitectureContractManifest,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureConformanceFinding:
        unverified = cast(ArchitectureAssertionUnverified, result)
        rule = f"architecture.conformance.{unverified.capability.value}"
        return ArchitectureConformanceFinding(
            fingerprint=unverified.fingerprint,
            contract_unit=unverified.unit_key,
            evidence=ArchitectureCoverageEvidence(
                diagram_revisions=self.unit(unverified, contract).diagram_revisions,
                capability=unverified.capability,
            ),
            expected={"coverage": "closed", "capability": unverified.capability.value},
            actual=(),
            support=unverified.support,
            state=unverified.state,
            finding_kind=unverified.kind,
            rule=rule,
            target=f"architecture-contract-unit:{unverified.unit_key}",
            message=unverified.explanation,
            next_action=(
                f"Provide complete {unverified.capability.value} extraction support before accepting closed coverage."
            ),
        )
