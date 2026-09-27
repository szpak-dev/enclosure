from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, ModifierContractFact
from ..observed.model import ObservedImplementationFact, ObservedModifierFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="modifier-comparison")
@dataclass(frozen=True)
class ModifierComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.MODIFIERS, init=False)
    name: str = field(default="modifiers", init=False)
    order: int = field(default=55, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(ModifierContractFact, expected)
        observed = cast(ObservedModifierFact, actual)
        return (
            contract.target_id == observed.target_id
            and contract.role == observed.role
            and contract.value == observed.value
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        target_id = cast(ObservedModifierFact, actual).target_id
        identity = target_id.removeprefix("attribute:").removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
