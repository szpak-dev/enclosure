from dataclasses import dataclass, field
from typing import cast

from pydantic import JsonValue
from wireup import injectable

from ....architecture_manifests.model import (
    ArchitectureAssertionFailure,
    ArchitectureAssertionResult,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
    ArchitectureExpectedFailure,
    ArchitectureFindingKind,
    ArchitectureUnexpectedFailure,
)
from ....architecture_manifests.observed.model import ObservedImplementationManifest
from ..model import (
    ArchitectureAssertionEvidence,
    ArchitectureConformanceFinding,
    ArchitectureUnexpectedEvidence,
)
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
        contract: ArchitectureContractManifest,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureConformanceFinding:
        failure = cast(ArchitectureAssertionFailure, result)
        expected: dict[str, JsonValue]
        if failure.kind == ArchitectureFindingKind.UNEXPECTED:
            expected = {"required": False}
            unexpected = cast(ArchitectureUnexpectedFailure, failure)
            evidence = ArchitectureUnexpectedEvidence(
                diagram_revisions=self.unit(unexpected, contract).diagram_revisions,
                source_symbol=unexpected.source_symbol,
            )
            target = unexpected.source_symbol
        else:
            expected = cast(ArchitectureExpectedFailure, failure).expected
            evidence = ArchitectureAssertionEvidence(
                diagram_evidence=failure.evidence,
                source_symbol=failure.assertion_id,
            )
            target = failure.assertion_id
        rule = f"architecture.conformance.{failure.capability.value}"
        return ArchitectureConformanceFinding(
            fingerprint=failure.fingerprint,
            contract_unit=failure.unit_key,
            evidence=evidence,
            expected=expected,
            actual=failure.actual,
            support=self.support(failure, observed),
            state=failure.state,
            finding_kind=failure.kind,
            rule=rule,
            target=target,
            message=(
                f"Architecture assertion {failure.assertion_id!r} is {failure.kind.value} "
                f"in contract unit {failure.unit_key!r}."
            ),
            next_action=f"Align {failure.assertion_id} with the accepted architecture contract.",
        )
