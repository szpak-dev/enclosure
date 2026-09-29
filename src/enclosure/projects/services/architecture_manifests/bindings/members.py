from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, MemberAssertion
from ..evidence.model import MemberEvidence
from .base import ArchitectureBindingRule
from .model import (
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureBindingState,
    ArchitectureBoundBinding,
)


@injectable(as_type=ArchitectureBindingRule, qualifier="member-binding")
@dataclass(frozen=True)
class MemberBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.MEMBER, init=False)
    name: str = field(default="members", init=False)
    order: int = field(default=30, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected = cast(MemberAssertion, assertion)
        owner = context.subject(assertion.unit_key, expected.owner_id)
        owner_binding = context.outcome(owner)
        if owner_binding.state != ArchitectureBindingState.BOUND:
            return self.blocked(assertion, "The architectural member owner is not uniquely bound.")
        owner_id = cast(ArchitectureBoundBinding, owner_binding).evidence_id
        candidates = tuple(
            cast(MemberEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.MEMBER
            and cast(MemberEvidence, item).owner_id == owner_id
            and cast(MemberEvidence, item).name == expected.name
            and cast(MemberEvidence, item).member_kind == expected.member_kind
        )
        return self.outcome(assertion, context, candidates)
