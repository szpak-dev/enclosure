from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, AttributeContractFact
from ..observed.model import ObservedAttributeFact, ObservedImplementationFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="attribute-comparison")
@dataclass(frozen=True)
class AttributeComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.ATTRIBUTES, init=False)
    name: str = field(default="attributes", init=False)
    order: int = field(default=50, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(AttributeContractFact, expected)
        observed = cast(ObservedAttributeFact, actual)
        return (
            contract.owner_id == observed.owner_id
            and contract.name == observed.name
            and contract.optional == observed.optional
            and contract.annotation == observed.annotation
            and contract.visibility == observed.visibility
            and contract.member_kind == observed.member_kind
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        identity = cast(ObservedAttributeFact, actual).owner_id.removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
