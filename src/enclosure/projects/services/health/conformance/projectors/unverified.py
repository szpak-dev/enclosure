from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ....architecture_manifests.model import (
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureAssertionUnverified,
    ArchitectureComparisonState,
)
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
    ) -> ArchitectureConformanceFinding:
        unverified = cast(ArchitectureAssertionUnverified, result)
        rule = f"architecture.conformance.{unverified.assertion_kind.value}"
        return ArchitectureConformanceFinding(
            fingerprint=unverified.fingerprint,
            contract_unit=unverified.unit_key,
            evidence=ArchitectureAssertionEvidence(
                diagram_evidence=unverified.evidence,
                implementation_evidence_ids=unverified.implementation_evidence_ids,
            ),
            expected=unverified.expected,
            observed=(),
            state=unverified.state,
            finding_kind=unverified.kind,
            owner=unverified.owner,
            rule=rule,
            target=unverified.assertion_id,
            message=unverified.explanation,
            next_action=self.next_action(unverified.owner, unverified.assertion_id),
        )
