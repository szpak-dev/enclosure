import json
from abc import ABC, abstractmethod
from hashlib import sha256

from ..assertions.model import (
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    ArchitectureParameter,
    ArchitectureTypeReference,
)
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
        expected_exclusions = {
            ArchitectureAssertionKind.MEMBER: {"owner_id"},
            ArchitectureAssertionKind.RELATIONSHIP: {"source_id", "target_id"},
            ArchitectureAssertionKind.ENTITY_FIELD: {"owner_id"},
        }.get(assertion.kind, set())
        observed_exclusions = {
            ArchitectureAssertionKind.MEMBER: {"owner_id"},
            ArchitectureAssertionKind.RELATIONSHIP: {"source_id", "target_reference"},
            ArchitectureAssertionKind.ENTITY_FIELD: {"owner_id"},
        }.get(evidence.kind, set())
        expected = ArchitectureSemanticValue(
            kind=assertion.kind,
            fields=assertion.model_dump(
                mode="json",
                exclude={
                    "id",
                    "unit_key",
                    "subject_id",
                    "kind",
                    "required",
                    "evidence",
                    *expected_exclusions,
                },
            ),
        )
        observed = ArchitectureSemanticValue(
            kind=evidence.kind,
            fields=evidence.model_dump(
                mode="json",
                exclude={"id", "kind", "locator", "reference", *observed_exclusions},
            ),
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

    def type_matches(
        self,
        expected: ArchitectureTypeReference,
        observed: ArchitectureTypeReference,
    ) -> bool:
        if expected.cardinality != observed.cardinality:
            return False
        if expected.name == "Unknown":
            return True
        return (
            expected.name == observed.name
            and len(expected.arguments) == len(observed.arguments)
            and all(
                self.type_matches(expected_argument, observed_argument)
                for expected_argument, observed_argument in zip(expected.arguments, observed.arguments, strict=True)
            )
        )

    def parameters_match(
        self,
        expected: tuple[ArchitectureParameter, ...],
        observed: tuple[ArchitectureParameter, ...],
    ) -> bool:
        return len(expected) == len(observed) and all(
            expected_parameter.name == observed_parameter.name
            and expected_parameter.position == observed_parameter.position
            and self.type_matches(expected_parameter.type, observed_parameter.type)
            for expected_parameter, observed_parameter in zip(expected, observed, strict=True)
        )
