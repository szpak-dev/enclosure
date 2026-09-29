from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ArtifactAssertion
from ..evidence.model import ArtifactEvidence
from .base import ArchitectureBindingRule
from .model import ArchitectureBindingContext, ArchitectureBindingOutcome


@injectable(as_type=ArchitectureBindingRule, qualifier="artifact-binding")
@dataclass(frozen=True)
class ArtifactBindingRule(ArchitectureBindingRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ARTIFACT, init=False)
    name: str = field(default="artifacts", init=False)
    order: int = field(default=10, init=False)

    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        expected = cast(ArtifactAssertion, assertion)
        candidates = tuple(
            cast(ArtifactEvidence, item)
            for item in context.observed.evidence
            if item.kind == ArchitectureAssertionKind.ARTIFACT
            and cast(ArtifactEvidence, item).path == expected.path
            and cast(ArtifactEvidence, item).artifact_kind == expected.artifact_kind
        )
        return self.outcome(assertion, context, candidates)
