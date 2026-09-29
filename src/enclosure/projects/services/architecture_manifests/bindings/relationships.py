from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, RelationshipAssertion
from ..evidence.model import RelationshipEvidence
from .base import ArchitectureBindingRule
from .model import (
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureBindingState,
    ArchitectureBoundBinding,
)


@injectable(as_type=ArchitectureBindingRule, qualifier="relationship-binding")
@dataclass(frozen=True)
class RelationshipBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.RELATIONSHIP, init=False)
    name: str = field(default="relationships", init=False)
    order: int = field(default=60, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected = cast(RelationshipAssertion, assertion)
        source = context.subject(assertion.unit_key, expected.source_id)
        target = context.subject(assertion.unit_key, expected.target_id)
        source_binding = context.outcome(source)
        target_binding = context.outcome(target)
        if (
            source_binding.state != ArchitectureBindingState.BOUND
            or target_binding.state != ArchitectureBindingState.BOUND
        ):
            return self.blocked(assertion, "The architectural relationship endpoints are not uniquely bound.")
        source_id = cast(ArchitectureBoundBinding, source_binding).evidence_id
        target_reference = context.evidence(cast(ArchitectureBoundBinding, target_binding).evidence_id).reference
        candidates = tuple(
            cast(RelationshipEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.RELATIONSHIP
            and cast(RelationshipEvidence, item).source_id == source_id
            and cast(RelationshipEvidence, item).target_reference == target_reference
        )
        return self.outcome(assertion, context, candidates)
