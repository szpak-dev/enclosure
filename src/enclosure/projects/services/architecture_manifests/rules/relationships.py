from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, RelationshipAssertion
from ..evidence.model import ImplementationEvidence, RelationshipEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="relationship-comparison")
@dataclass(frozen=True)
class RelationshipComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.RELATIONSHIP, init=False)
    name: str = field(default="relationships", init=False)
    order: int = field(default=40, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected = cast(RelationshipAssertion, assertion)
        observed = cast(RelationshipEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected.relationship_kind == observed.relationship_kind
            and expected.source_cardinality == observed.source_cardinality
            and expected.target_cardinality == observed.target_cardinality,
        )
