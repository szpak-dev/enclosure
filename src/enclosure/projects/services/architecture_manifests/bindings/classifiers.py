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
        evidence = tuple(
            cast(ClassifierEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.CLASSIFIER
        )
        references = {item.element_id for item in expected.evidence}
        exact = tuple(item for item in evidence if item.reference in references)
        if exact:
            return self.outcome(assertion, context, exact)
        candidates = tuple(item for item in evidence if item.name == expected.name)
        return self.outcome(assertion, context, candidates)
