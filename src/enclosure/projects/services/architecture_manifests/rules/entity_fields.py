from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, EntityFieldAssertion
from ..evidence.model import EntityFieldEvidence, ImplementationEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="entity-field-comparison")
@dataclass(frozen=True)
class EntityFieldComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ENTITY_FIELD, init=False)
    name: str = field(default="entity-fields", init=False)
    order: int = field(default=60, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected = cast(EntityFieldAssertion, assertion)
        observed = cast(EntityFieldEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected.name == observed.name
            and self.type_matches(expected.type, observed.type)
            and expected.keys == observed.keys
            and expected.cardinality == observed.cardinality,
        )
