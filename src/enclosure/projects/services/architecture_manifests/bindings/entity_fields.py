from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, EntityFieldAssertion
from ..evidence.model import EntityFieldEvidence
from .base import ArchitectureBindingRule
from .model import (
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureBindingState,
    ArchitectureBoundBinding,
)


@injectable(as_type=ArchitectureBindingRule, qualifier="entity-field-binding")
@dataclass(frozen=True)
class EntityFieldBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ENTITY_FIELD, init=False)
    name: str = field(default="entity-fields", init=False)
    order: int = field(default=50, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected = cast(EntityFieldAssertion, assertion)
        owner = context.subject(assertion.unit_key, expected.owner_id)
        owner_binding = context.outcome(owner)
        if owner_binding.state != ArchitectureBindingState.BOUND:
            return self.blocked(assertion, "The architectural entity owner is not uniquely bound.")
        owner_id = cast(ArchitectureBoundBinding, owner_binding).evidence_id
        candidates = tuple(
            cast(EntityFieldEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.ENTITY_FIELD
            and cast(EntityFieldEvidence, item).owner_id == owner_id
            and cast(EntityFieldEvidence, item).name == expected.name
        )
        return self.outcome(assertion, context, candidates)
