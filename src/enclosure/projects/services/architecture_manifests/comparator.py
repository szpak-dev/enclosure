import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from operator import attrgetter
from typing import cast

from wireup import injectable

from ...errors import ProjectsError
from .assertions.model import ArchitectureAssertion, ArchitectureAssertionKind
from .bindings.model import (
    ArchitectureBindingOutcome,
    ArchitectureBindingState,
    ArchitectureBoundBinding,
    ArchitectureRealizationMap,
    ArchitectureUnsupportedBinding,
)
from .evidence.model import ImplementationEvidence, ImplementationEvidenceManifest
from .identity import ArchitectureComparisonIdentity
from .model import (
    ArchitectureAssertionFailure,
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureAssertionUnverified,
    ArchitectureComparison,
    ArchitectureComparisonConclusion,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
    ArchitectureSemanticValue,
)
from .rules.base import ArchitectureComparisonRule
from .rules.coverage import ArchitectureCoverageEvaluator


@injectable
@dataclass(frozen=True)
class ArchitectureContractComparator:
    rules: Sequence[ArchitectureComparisonRule]
    coverage: ArchitectureCoverageEvaluator
    identity: ArchitectureComparisonIdentity = field(default_factory=ArchitectureComparisonIdentity, init=False)

    def compare(
        self,
        expected: ArchitectureContractManifest,
        observed: ImplementationEvidenceManifest,
        realization: ArchitectureRealizationMap,
    ) -> ArchitectureComparison:
        rules = tuple(sorted(self.rules, key=attrgetter("order", "name")))
        kinds = tuple(rule.assertion_kind for rule in rules)
        if len(kinds) != len(set(kinds)) or set(kinds) != set(ArchitectureAssertionKind):
            raise ProjectsError("Architecture comparison requires exactly one rule per assertion kind.")
        indexed_rules = {rule.assertion_kind: rule for rule in rules}
        bindings = {(binding.unit_key, binding.assertion_id): binding for binding in realization.bindings}
        evidence = {item.id: item for item in observed.evidence}
        results: list[ArchitectureAssertionResult] = []
        for unit in expected.units:
            for assertion in unit.assertions:
                if not assertion.required:
                    continue
                binding = bindings[(unit.key, assertion.id)]
                if binding.state == ArchitectureBindingState.BOUND:
                    implementation = evidence[cast(ArchitectureBoundBinding, binding).evidence_id]
                    results.append(indexed_rules[assertion.kind].compare(assertion, implementation))
                else:
                    results.append(self.binding_result(assertion, binding, evidence))
        results.extend(self.coverage.evaluate(expected, observed, realization))
        ordered_results = tuple(
            sorted(results, key=attrgetter("unit_key", "assertion_kind", "assertion_id", "fingerprint"))
        )
        passed = sum(result.state == ArchitectureComparisonState.PASS for result in ordered_results)
        failed = sum(result.state == ArchitectureComparisonState.FAIL for result in ordered_results)
        unverified = sum(result.state == ArchitectureComparisonState.UNVERIFIED for result in ordered_results)
        if failed:
            conclusion = ArchitectureComparisonConclusion.DOES_NOT_CONFORM
        elif unverified:
            conclusion = ArchitectureComparisonConclusion.UNVERIFIED
        else:
            conclusion = ArchitectureComparisonConclusion.CONFORMS
        payload = {
            "schema_version": self.identity.schema_version,
            "contract_digest": expected.digest,
            "implementation_digest": observed.digest,
            "realization_digest": realization.digest,
            "source_digest": observed.source_digest,
            "conclusion": conclusion.value,
            "results": [result.model_dump(mode="json") for result in ordered_results],
            "passed": passed,
            "failed": failed,
            "unverified": unverified,
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureComparison(
            schema_version=self.identity.schema_version,
            contract_digest=expected.digest,
            implementation_digest=observed.digest,
            realization_digest=realization.digest,
            source_digest=observed.source_digest,
            conclusion=conclusion,
            results=ordered_results,
            passed=passed,
            failed=failed,
            unverified=unverified,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

    def binding_result(
        self,
        assertion: ArchitectureAssertion,
        binding: ArchitectureBindingOutcome,
        evidence: dict[str, ImplementationEvidence],
    ) -> ArchitectureAssertionResult:
        expected = self.assertion_value(assertion)
        observed = tuple(self.evidence_value(evidence[candidate]) for candidate in binding.candidate_ids)
        if binding.state == ArchitectureBindingState.MISSING:
            state = ArchitectureComparisonState.FAIL
            kind = ArchitectureFindingKind.MISSING
            owner = ArchitectureFindingOwner.IMPLEMENTATION
            explanation = ""
        elif binding.state == ArchitectureBindingState.AMBIGUOUS:
            state = ArchitectureComparisonState.UNVERIFIED
            kind = ArchitectureFindingKind.AMBIGUOUS
            owner = ArchitectureFindingOwner.REALIZATION
            explanation = "Multiple implementation candidates match the architectural identity."
        else:
            state = ArchitectureComparisonState.UNVERIFIED
            kind = ArchitectureFindingKind.UNSUPPORTED
            owner = ArchitectureFindingOwner.OBSERVER
            explanation = cast(ArchitectureUnsupportedBinding, binding).explanation
        fingerprint = self.fingerprint(assertion, binding, state, expected, observed)
        if state == ArchitectureComparisonState.FAIL:
            return ArchitectureAssertionFailure(
                fingerprint=fingerprint,
                assertion_id=assertion.id,
                unit_key=assertion.unit_key,
                assertion_kind=assertion.kind,
                scope=ArchitectureAssertionScope.ASSERTION,
                state=state,
                owner=owner,
                evidence=assertion.evidence,
                implementation_evidence_ids=binding.candidate_ids,
                kind=kind,
                expected=expected,
                observed=observed,
            )
        return ArchitectureAssertionUnverified(
            fingerprint=fingerprint,
            assertion_id=assertion.id,
            unit_key=assertion.unit_key,
            assertion_kind=assertion.kind,
            scope=ArchitectureAssertionScope.ASSERTION,
            state=state,
            owner=owner,
            evidence=assertion.evidence,
            implementation_evidence_ids=binding.candidate_ids,
            kind=kind,
            expected=expected,
            diagram_revisions=(),
            explanation=explanation,
        )

    def assertion_value(self, assertion: ArchitectureAssertion) -> ArchitectureSemanticValue:
        return ArchitectureSemanticValue(
            kind=assertion.kind,
            fields=assertion.model_dump(
                mode="json",
                exclude={"id", "unit_key", "subject_id", "kind", "required", "evidence"},
            ),
        )

    def evidence_value(self, evidence: ImplementationEvidence) -> ArchitectureSemanticValue:
        return ArchitectureSemanticValue(
            kind=evidence.kind,
            fields=evidence.model_dump(mode="json", exclude={"id", "kind", "locator", "reference"}),
        )

    def fingerprint(
        self,
        assertion: ArchitectureAssertion,
        binding: ArchitectureBindingOutcome,
        state: ArchitectureComparisonState,
        expected: ArchitectureSemanticValue,
        observed: tuple[ArchitectureSemanticValue, ...],
    ) -> str:
        canonical = json.dumps(
            {
                "unit": assertion.unit_key,
                "assertion": assertion.id,
                "binding": binding.model_dump(mode="json"),
                "state": state.value,
                "expected": expected.model_dump(mode="json"),
                "observed": [value.model_dump(mode="json") for value in observed],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()
