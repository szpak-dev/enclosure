import json
from dataclasses import dataclass
from hashlib import sha256

from wireup import injectable

from ...architecture_contracts.model import ArchitectureContractCoverage
from ..assertions.model import ArchitectureAssertionKind
from ..bindings.model import ArchitectureBindingState, ArchitectureRealizationMap
from ..evidence.model import ArchitectureSupportState, ImplementationEvidence, ImplementationEvidenceManifest
from ..model import (
    ArchitectureAssertionFailure,
    ArchitectureAssertionResult,
    ArchitectureAssertionScope,
    ArchitectureAssertionUnverified,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
    ArchitectureSemanticValue,
)


@injectable
@dataclass(frozen=True)
class ArchitectureCoverageEvaluator:
    def evaluate(
        self,
        expected: ArchitectureContractManifest,
        observed: ImplementationEvidenceManifest,
        realization: ArchitectureRealizationMap,
    ) -> tuple[ArchitectureAssertionResult, ...]:
        results: list[ArchitectureAssertionResult] = []
        for unit in expected.units:
            if unit.coverage != ArchitectureContractCoverage.CLOSED:
                continue
            bound_ids = {
                candidate_id
                for binding in realization.bindings
                if binding.unit_key == unit.key and binding.state == ArchitectureBindingState.BOUND
                for candidate_id in binding.candidate_ids
            }
            for kind in ArchitectureAssertionKind:
                support = observed.support(kind)
                if support.support != ArchitectureSupportState.SUPPORTED:
                    assertion_id = f"coverage:{kind.value}"
                    results.append(
                        ArchitectureAssertionUnverified(
                            fingerprint=self.fingerprint(
                                unit.key,
                                assertion_id,
                                ArchitectureComparisonState.UNVERIFIED,
                                {"explanation": support.explanation},
                            ),
                            assertion_id=assertion_id,
                            unit_key=unit.key,
                            assertion_kind=kind,
                            scope=ArchitectureAssertionScope.COVERAGE,
                            state=ArchitectureComparisonState.UNVERIFIED,
                            owner=ArchitectureFindingOwner.OBSERVER,
                            evidence=(),
                            implementation_evidence_ids=(),
                            kind=ArchitectureFindingKind.UNSUPPORTED,
                            expected=ArchitectureSemanticValue(
                                kind=kind,
                                fields={"coverage": "closed"},
                            ),
                            diagram_revisions=unit.diagram_revisions,
                            explanation=support.explanation or "Closed coverage lacks complete evidence support.",
                        )
                    )
                    continue
                for item in observed.evidence:
                    if item.kind != kind or item.id in bound_ids or not self.inside(unit.source_root, item):
                        continue
                    if any(
                        item.locator.path == exclusion.path or item.locator.path.startswith(f"{exclusion.path}/")
                        for exclusion in unit.exclusions
                    ):
                        continue
                    assertion_id = f"unexpected:{item.id}"
                    observed_value = ArchitectureSemanticValue(
                        kind=item.kind,
                        fields=item.model_dump(
                            mode="json",
                            exclude={"id", "kind", "locator", "reference"},
                        ),
                    )
                    expected_value = ArchitectureSemanticValue(
                        kind=item.kind,
                        fields={"declared": False},
                    )
                    results.append(
                        ArchitectureAssertionFailure(
                            fingerprint=self.fingerprint(
                                unit.key,
                                assertion_id,
                                ArchitectureComparisonState.FAIL,
                                observed_value.model_dump(mode="json"),
                            ),
                            assertion_id=assertion_id,
                            unit_key=unit.key,
                            assertion_kind=item.kind,
                            scope=ArchitectureAssertionScope.COVERAGE,
                            state=ArchitectureComparisonState.FAIL,
                            owner=ArchitectureFindingOwner.IMPLEMENTATION,
                            evidence=(),
                            implementation_evidence_ids=(item.id,),
                            kind=ArchitectureFindingKind.UNEXPECTED,
                            expected=expected_value,
                            observed=(observed_value,),
                        )
                    )
        return tuple(sorted(results, key=lambda result: (result.unit_key, result.assertion_id)))

    def inside(self, source_root: str, evidence: ImplementationEvidence) -> bool:
        return (
            source_root == "."
            or evidence.locator.path == source_root
            or evidence.locator.path.startswith(f"{source_root}/")
        )

    def fingerprint(
        self,
        unit_key: str,
        assertion_id: str,
        state: ArchitectureComparisonState,
        detail: object,
    ) -> str:
        canonical = json.dumps(
            {"unit": unit_key, "assertion": assertion_id, "state": state.value, "detail": detail},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()
