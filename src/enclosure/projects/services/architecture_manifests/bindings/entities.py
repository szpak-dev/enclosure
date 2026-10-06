from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import (
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    EntityAssertion,
)
from .base import ArchitectureBindingRule
from .model import ArchitectureBindingContext, ArchitectureBindingOutcome


@injectable(as_type=ArchitectureBindingRule, qualifier="entity-binding")
@dataclass(frozen=True)
class EntityBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ENTITY, init=False)
    name: str = field(default="entities", init=False)
    order: int = field(default=40, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected_entity = cast(EntityAssertion, assertion)
        candidates = context.index.entities(expected_entity.name)
        return self.outcome(assertion, context, candidates)
