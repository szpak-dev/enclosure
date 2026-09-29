import json
from abc import ABC, abstractmethod
from hashlib import sha256

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind
from ..evidence.model import ImplementationEvidence
from ..model import (
    ArchitectureAssertionFailure,
    ArchitectureAssertionPass,
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureComparisonState,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
    ArchitectureSemanticValue,
)


class ArchitectureComparisonRule(ABC):
    assertion_kind: ArchitectureAssertionKind
    name: str
    order: int

    @abstractmethod
    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        raise NotImplementedError

    def result(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
        matches: bool,
    ) -> ArchitectureAssertionResult:
        expected = ArchitectureSemanticValue(
            kind=assertion.kind,
            fields=assertion.model_dump(
                mode="json",
                exclude={"id", "unit_key", "subject_id", "kind", "required", "evidence"},
            ),
        )
        observed = ArchitectureSemanticValue(
            kind=evidence.kind,
            fields=evidence.model_dump(mode="json", exclude={"id", "kind", "locator", "reference"}),
        )
        values = {
            "unit": assertion.unit_key,
            "assertion": assertion.id,
            "evidence": evidence.id,
            "state": ArchitectureComparisonState.PASS.value if matches else ArchitectureComparisonState.FAIL.value,
            "expected": expected.model_dump(mode="json"),
            "observed": observed.model_dump(mode="json"),
        }
        canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
        if matches:
            return ArchitectureAssertionPass(
                fingerprint=fingerprint,
                assertion_id=assertion.id,
                unit_key=assertion.unit_key,
                assertion_kind=assertion.kind,
                scope=ArchitectureAssertionScope.ASSERTION,
                state=ArchitectureComparisonState.PASS,
                owner=ArchitectureFindingOwner.IMPLEMENTATION,
                evidence=assertion.evidence,
                implementation_evidence_ids=(evidence.id,),
                evidence_id=evidence.id,
            )
        return ArchitectureAssertionFailure(
            fingerprint=fingerprint,
            assertion_id=assertion.id,
            unit_key=assertion.unit_key,
            assertion_kind=assertion.kind,
            scope=ArchitectureAssertionScope.ASSERTION,
            state=ArchitectureComparisonState.FAIL,
            owner=ArchitectureFindingOwner.IMPLEMENTATION,
            evidence=assertion.evidence,
            implementation_evidence_ids=(evidence.id,),
            kind=ArchitectureFindingKind.MISMATCHED,
            expected=expected,
            observed=(observed,),
        )
