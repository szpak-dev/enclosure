from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ClassifierAssertion
from ..evidence.model import ClassifierEvidence
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
        candidates = tuple(
            cast(ClassifierEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.CLASSIFIER
            and cast(ClassifierEvidence, item).name == expected.name
        )
        return self.outcome(assertion, context, candidates)
