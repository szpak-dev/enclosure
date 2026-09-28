import json
from abc import ABC, abstractmethod
from hashlib import sha256

from ...architecture_contracts.model import ArchitectureContractCoverage
from ..facts.model import (
    ArchitectureContractFact,
    ArchitectureDiagramEvidence,
    ArchitectureFactCapability,
)
from ..model import (
    ArchitectureAssertionPass,
    ArchitectureAssertionResult,
    ArchitectureAssertionUnverified,
    ArchitectureComparisonState,
    ArchitectureContractManifestUnit,
    ArchitectureExpectedFailure,
    ArchitectureFindingKind,
    ArchitectureSupportState,
    ArchitectureUnexpectedFailure,
)
from ..observed.model import ObservedImplementationFact, ObservedImplementationManifest


class ArchitectureComparisonRule(ABC):
    capability: ArchitectureFactCapability
    name: str
    order: int

    def governs(self, actual: ObservedImplementationFact) -> bool:
        return True

    def unverified(
        self,
        unit_key: str,
        assertion_id: str,
        evidence: tuple[ArchitectureDiagramEvidence, ...],
        support: ArchitectureSupportState,
        explanation: str,
    ) -> ArchitectureAssertionUnverified:
        values = {
            "unit": unit_key,
            "assertion": assertion_id,
            "state": ArchitectureComparisonState.UNVERIFIED.value,
            "support": support.value,
            "explanation": explanation,
        }
        canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureAssertionUnverified(
            fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
            assertion_id=assertion_id,
            unit_key=unit_key,
            capability=self.capability,
            state=ArchitectureComparisonState.UNVERIFIED,
            evidence=evidence,
            kind=ArchitectureFindingKind.UNSUPPORTED,
            support=support,
            explanation=explanation,
        )

    def compare(
        self,
        unit: ArchitectureContractManifestUnit,
        observed: ObservedImplementationManifest,
    ) -> tuple[ArchitectureAssertionResult, ...]:
        expected = tuple(fact for fact in unit.facts if fact.required and fact.capability == self.capability)
        actual = tuple(fact for fact in observed.facts if fact.capability == self.capability and self.governs(fact))
        coverage = {item.capability: item for item in observed.capabilities}[self.capability]
        support = coverage.support
        explanation = coverage.explanation
        results: list[ArchitectureAssertionResult] = []
        declared_ids = {fact.id for fact in unit.facts if fact.capability == self.capability}
        for fact in expected:
            if support == ArchitectureSupportState.UNSUPPORTED:
                results.append(
                    self.unverified(
                        unit.key,
                        fact.id,
                        fact.evidence,
                        support,
                        explanation,
                    )
                )
                continue
            candidates = tuple(item for item in actual if item.id == fact.id)
            if len(candidates) > 1:
                kind = ArchitectureFindingKind.AMBIGUOUS
            elif len(candidates) == 1:
                if self.matches(fact, candidates[0]):
                    values = {
                        "unit": unit.key,
                        "assertion": fact.id,
                        "state": ArchitectureComparisonState.PASS.value,
                        "actual": candidates[0].id,
                    }
                    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    results.append(
                        ArchitectureAssertionPass(
                            fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
                            assertion_id=fact.id,
                            unit_key=unit.key,
                            capability=self.capability,
                            state=ArchitectureComparisonState.PASS,
                            evidence=fact.evidence,
                            actual_id=candidates[0].id,
                        )
                    )
                    continue
                else:
                    kind = ArchitectureFindingKind.MISMATCHED
            elif support == ArchitectureSupportState.SUPPORTED:
                kind = ArchitectureFindingKind.MISSING
            else:
                results.append(
                    self.unverified(
                        unit.key,
                        fact.id,
                        fact.evidence,
                        support,
                        explanation,
                    )
                )
                continue
            expected_value = fact.model_dump(mode="json", exclude={"evidence"})
            actual_values = tuple(item.model_dump(mode="json") for item in sorted(candidates, key=lambda item: item.id))
            values = {
                "unit": unit.key,
                "assertion": fact.id,
                "state": ArchitectureComparisonState.FAIL.value,
                "kind": kind.value,
                "expected": expected_value,
                "actual": actual_values,
            }
            canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            results.append(
                ArchitectureExpectedFailure(
                    fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
                    assertion_id=fact.id,
                    unit_key=unit.key,
                    capability=self.capability,
                    state=ArchitectureComparisonState.FAIL,
                    evidence=fact.evidence,
                    kind=kind,
                    expected=expected_value,
                    actual=actual_values,
                )
            )
        if unit.coverage == ArchitectureContractCoverage.CLOSED and support != ArchitectureSupportState.SUPPORTED:
            results.append(
                self.unverified(
                    unit.key,
                    f"coverage:{self.capability.value}",
                    (),
                    support,
                    explanation,
                )
            )
        if unit.coverage == ArchitectureContractCoverage.CLOSED and support != ArchitectureSupportState.UNSUPPORTED:
            unexpected = tuple(
                item
                for item in actual
                if item.id not in declared_ids
                and (
                    unit.source_root == "."
                    or self.path(item) == unit.source_root
                    or self.path(item).startswith(f"{unit.source_root}/")
                )
                and not any(
                    self.path(item) == exclusion.path or self.path(item).startswith(f"{exclusion.path}/")
                    for exclusion in unit.exclusions
                )
            )
            for item in unexpected:
                actual_value = item.model_dump(mode="json")
                assertion_id = f"unexpected:{item.id}"
                values = {
                    "unit": unit.key,
                    "assertion": assertion_id,
                    "state": ArchitectureComparisonState.FAIL.value,
                    "kind": ArchitectureFindingKind.UNEXPECTED.value,
                    "actual": actual_value,
                }
                canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                results.append(
                    ArchitectureUnexpectedFailure(
                        fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
                        assertion_id=assertion_id,
                        unit_key=unit.key,
                        capability=self.capability,
                        state=ArchitectureComparisonState.FAIL,
                        evidence=(),
                        kind=ArchitectureFindingKind.UNEXPECTED,
                        actual=(actual_value,),
                    )
                )
        return tuple(sorted(results, key=lambda result: (result.assertion_id, result.fingerprint)))

    @abstractmethod
    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        raise NotImplementedError

    @abstractmethod
    def path(self, actual: ObservedImplementationFact) -> str:
        raise NotImplementedError
