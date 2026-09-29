from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ....architecture_manifests.model import (
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureAssertionUnverified,
    ArchitectureComparisonState,
)
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
    ) -> ArchitectureConformanceFinding:
        unverified = cast(ArchitectureAssertionUnverified, result)
        rule = f"architecture.conformance.{unverified.assertion_kind.value}"
        return ArchitectureConformanceFinding(
            fingerprint=unverified.fingerprint,
            contract_unit=unverified.unit_key,
            evidence=ArchitectureCoverageEvidence(
                diagram_revisions=unverified.diagram_revisions,
                assertion_kind=unverified.assertion_kind,
            ),
            expected=unverified.expected,
            observed=(),
            state=unverified.state,
            finding_kind=unverified.kind,
            owner=unverified.owner,
            rule=rule,
            target=f"architecture-contract-unit:{unverified.unit_key}",
            message=unverified.explanation,
            next_action=self.next_action(unverified.owner, unverified.assertion_id),
        )
