from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, InheritanceContractFact
from ..observed.model import ObservedImplementationFact, ObservedInheritanceFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="inheritance-comparison")
@dataclass(frozen=True)
class InheritanceComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.INHERITANCE, init=False)
    name: str = field(default="inheritance", init=False)
    order: int = field(default=70, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(InheritanceContractFact, expected)
        observed = cast(ObservedInheritanceFact, actual)
        return (
            contract.owner_id == observed.owner_id
            and contract.kind == observed.kind
            and contract.target == observed.target
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        identity = cast(ObservedInheritanceFact, actual).owner_id.removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
