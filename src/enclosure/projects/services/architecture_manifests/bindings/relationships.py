from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, RelationshipAssertion
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
        candidates = context.index.relationships(source_id, target_reference)
        semantic = tuple(
            item
            for item in candidates
            if item.relationship_kind == expected.relationship_kind
            and item.source_cardinality == expected.source_cardinality
            and item.target_cardinality == expected.target_cardinality
        )
        if semantic:
            ordered = tuple(sorted(semantic, key=lambda item: item.id))
            return ArchitectureBoundBinding(
                unit_key=assertion.unit_key,
                assertion_id=assertion.id,
                state=ArchitectureBindingState.BOUND,
                candidate_ids=tuple(item.id for item in ordered),
                evidence_id=ordered[0].id,
            )
        exact = tuple(item for item in candidates if item.relationship_kind == expected.relationship_kind)
        if exact:
            semantic_values = {
                (item.relationship_kind, item.source_cardinality, item.target_cardinality) for item in exact
            }
            if len(semantic_values) == 1:
                ordered = tuple(sorted(exact, key=lambda item: item.id))
                return ArchitectureBoundBinding(
                    unit_key=assertion.unit_key,
                    assertion_id=assertion.id,
                    state=ArchitectureBindingState.BOUND,
                    candidate_ids=tuple(item.id for item in ordered),
                    evidence_id=ordered[0].id,
                )
            return self.outcome(assertion, context, exact)
        return self.outcome(assertion, context, candidates)
