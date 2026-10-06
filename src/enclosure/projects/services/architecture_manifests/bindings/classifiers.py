from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ClassifierAssertion
from .base import ArchitectureBindingRule
from .model import ArchitectureBindingContext, ArchitectureBindingOutcome


@injectable(as_type=ArchitectureBindingRule, qualifier="classifier-binding")
@dataclass(frozen=True)
class ClassifierBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.CLASSIFIER, init=False)
    name: str = field(default="classifiers", init=False)
    order: int = field(default=20, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected = cast(ClassifierAssertion, assertion)
        references = tuple(item.element_id for item in expected.evidence)
        candidates = context.index.classifiers(references, expected.name)
        return self.outcome(assertion, context, candidates)
