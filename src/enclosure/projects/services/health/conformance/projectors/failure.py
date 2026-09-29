from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ....architecture_manifests.model import (
    ArchitectureAssertionFailure,
    ArchitectureAssertionResult,
    ArchitectureComparisonState,
    ArchitectureFindingKind,
)
from ..model import ArchitectureAssertionEvidence, ArchitectureConformanceFinding, ArchitectureUnexpectedEvidence
from .base import ArchitectureConformanceFindingProjector


@injectable(as_type=ArchitectureConformanceFindingProjector, qualifier="architecture-failure-finding")
@dataclass(frozen=True)
class ArchitectureFailureFindingProjector(ArchitectureConformanceFindingProjector):
    name: str = field(default="failure", init=False)
    order: int = field(default=10, init=False)

    def supports(self, result: ArchitectureAssertionResult) -> bool:
        return result.state == ArchitectureComparisonState.FAIL

    def project(
        self,
        result: ArchitectureAssertionResult,
    ) -> ArchitectureConformanceFinding:
        failure = cast(ArchitectureAssertionFailure, result)
        if failure.kind == ArchitectureFindingKind.UNEXPECTED:
            evidence = ArchitectureUnexpectedEvidence(
                implementation_evidence_ids=failure.implementation_evidence_ids,
            )
        else:
            evidence = ArchitectureAssertionEvidence(
                diagram_evidence=failure.evidence,
                implementation_evidence_ids=failure.implementation_evidence_ids,
            )
        rule = f"architecture.conformance.{failure.assertion_kind.value}"
        return ArchitectureConformanceFinding(
            fingerprint=failure.fingerprint,
            contract_unit=failure.unit_key,
            evidence=evidence,
            expected=failure.expected,
            observed=failure.observed,
            state=failure.state,
            finding_kind=failure.kind,
            owner=failure.owner,
            rule=rule,
            target=failure.assertion_id,
            message=(
                f"Architecture assertion {failure.assertion_id!r} is {failure.kind.value} "
                f"in contract unit {failure.unit_key!r}; remediation belongs to {failure.owner.value}."
            ),
            next_action=self.next_action(failure.owner, failure.assertion_id),
        )
