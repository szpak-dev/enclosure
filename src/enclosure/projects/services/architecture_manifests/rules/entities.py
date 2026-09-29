from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import (
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    EntityAssertion,
)
from ..evidence.model import EntityEvidence, ImplementationEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="entity-comparison")
@dataclass(frozen=True)
class EntityComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ENTITY, init=False)
    name: str = field(default="entities", init=False)
    order: int = field(default=50, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected_entity = cast(EntityAssertion, assertion)
        observed_entity = cast(EntityEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected_entity.name.replace("_", "").casefold() == observed_entity.name.replace("_", "").casefold(),
        )
