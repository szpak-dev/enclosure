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
from ..model import ArchitectureAssertionEvidence, ArchitectureConformanceFinding
from .base import ArchitectureConformanceFindingProjector


@injectable(as_type=ArchitectureConformanceFindingProjector, qualifier="architecture-unverified-finding")
@dataclass(frozen=True)
class ArchitectureUnverifiedFindingProjector(ArchitectureConformanceFindingProjector):
    name: str = field(default="unverified", init=False)
    order: int = field(default=20, init=False)

    def supports(self, result: ArchitectureAssertionResult) -> bool:
        return (
            result.state == ArchitectureComparisonState.UNVERIFIED
            and result.scope == ArchitectureAssertionScope.ASSERTION
        )

    def project(
        self,
        result: ArchitectureAssertionResult,
        contract: ArchitectureContractManifest,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureConformanceFinding:
        unverified = cast(ArchitectureAssertionUnverified, result)
        expected = self.expected(unverified, contract)
        rule = f"architecture.conformance.{unverified.capability.value}"
        return ArchitectureConformanceFinding(
            fingerprint=unverified.fingerprint,
            contract_unit=unverified.unit_key,
            evidence=ArchitectureAssertionEvidence(
                diagram_evidence=unverified.evidence,
                source_symbol=unverified.assertion_id,
            ),
            expected=expected.model_dump(mode="json", exclude={"evidence"}),
            actual=(),
            support=unverified.support,
            state=unverified.state,
            finding_kind=unverified.kind,
            rule=rule,
            target=unverified.assertion_id,
            message=unverified.explanation,
            next_action=(
                f"Provide complete {unverified.capability.value} evidence for {unverified.assertion_id} "
                "before accepting conformance."
            ),
        )
