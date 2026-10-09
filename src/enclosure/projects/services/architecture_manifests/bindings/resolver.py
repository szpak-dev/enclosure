import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter

from wireup import injectable

from ....errors import ProjectsError
from ..assertions.model import ArchitectureAssertionKind
from ..evidence.model import ImplementationEvidenceManifest
from ..model import ArchitectureContractManifest
from .base import ArchitectureBindingRule
from .indexer import ArchitectureEvidenceIndexer
from .model import (
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureRealizationMap,
)


@injectable
@dataclass(frozen=True)
class ArchitectureBindingResolver:
    rules: Sequence[ArchitectureBindingRule]
    indexer: ArchitectureEvidenceIndexer

    def resolve(
        self,
        expected: ArchitectureContractManifest,
        observed: ImplementationEvidenceManifest,
    ) -> ArchitectureRealizationMap:
        rules = tuple(sorted(self.rules, key=attrgetter("order", "name")))
        kinds = tuple(rule.assertion_kind for rule in rules)
        if len(kinds) != len(set(kinds)) or set(kinds) != set(ArchitectureAssertionKind):
            raise ProjectsError("Architecture binding requires exactly one rule per assertion kind.")
        indexed_rules = {rule.assertion_kind: rule for rule in rules}
        assertions = tuple(assertion for unit in expected.units for assertion in unit.assertions)
        ordered_assertions = tuple(
            sorted(
                assertions,
                key=lambda assertion: (
                    indexed_rules[assertion.kind].order,
                    assertion.unit_key,
                    assertion.id,
                ),
            )
        )
        outcomes: list[ArchitectureBindingOutcome] = []
        evidence_index = self.indexer.index(observed)
        for assertion in ordered_assertions:
            context = ArchitectureBindingContext(
                observed=observed,
                index=evidence_index,
                assertions=assertions,
                outcomes=tuple(outcomes),
            )
            outcomes.append(indexed_rules[assertion.kind].bind(assertion, context))
        bindings = tuple(sorted(outcomes, key=attrgetter("unit_key", "assertion_id", "state")))
        payload = {"bindings": [binding.model_dump(mode="json") for binding in bindings]}
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureRealizationMap(
            bindings=bindings,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )
