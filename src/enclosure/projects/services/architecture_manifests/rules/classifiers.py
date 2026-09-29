from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ClassifierAssertion
from ..evidence.model import ClassifierEvidence, ImplementationEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="classifier-comparison")
@dataclass(frozen=True)
class ClassifierComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.CLASSIFIER, init=False)
    name: str = field(default="classifiers", init=False)
    order: int = field(default=20, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected = cast(ClassifierAssertion, assertion)
        observed = cast(ClassifierEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected.name == observed.name
            and expected.classifier_kind == observed.classifier_kind
            and expected.abstract == observed.abstract,
        )
