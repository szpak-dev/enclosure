from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ArtifactAssertion
from ..evidence.model import ArtifactEvidence, ImplementationEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="artifact-comparison")
@dataclass(frozen=True)
class ArtifactComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.ARTIFACT, init=False)
    name: str = field(default="artifacts", init=False)
    order: int = field(default=10, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected = cast(ArtifactAssertion, assertion)
        observed = cast(ArtifactEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected.path == observed.path and expected.artifact_kind == observed.artifact_kind,
        )
