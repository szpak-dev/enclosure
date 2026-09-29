from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, MemberAssertion
from ..evidence.model import ImplementationEvidence, MemberEvidence
from ..model import ArchitectureAssertionResult
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="member-comparison")
@dataclass(frozen=True)
class MemberComparisonRule(ArchitectureComparisonRule):
    assertion_kind: ArchitectureAssertionKind = field(default=ArchitectureAssertionKind.MEMBER, init=False)
    name: str = field(default="members", init=False)
    order: int = field(default=30, init=False)

    def compare(
        self,
        assertion: ArchitectureAssertion,
        evidence: ImplementationEvidence,
    ) -> ArchitectureAssertionResult:
        expected = cast(MemberAssertion, assertion)
        observed = cast(MemberEvidence, evidence)
        return self.result(
            assertion,
            evidence,
            expected.name == observed.name
            and expected.member_kind == observed.member_kind
            and expected.type == observed.type
            and expected.visibility == observed.visibility
            and expected.ownership == observed.ownership
            and expected.abstract == observed.abstract
            and expected.parameters == observed.parameters,
        )
