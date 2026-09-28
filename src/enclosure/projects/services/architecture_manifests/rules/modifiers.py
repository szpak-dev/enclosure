from dataclasses import dataclass, field

from wireup import injectable

from ....errors import ProjectsError
from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability
from ..observed.model import ObservedImplementationFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="modifier-comparison")
@dataclass(frozen=True)
class ModifierComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.MODIFIERS, init=False)
    name: str = field(default="modifiers", init=False)
    order: int = field(default=55, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        raise ProjectsError(f"Modifier comparison facts are not implemented for {expected.id!r} and {actual.id!r}.")

    def path(self, actual: ObservedImplementationFact) -> str:
        raise ProjectsError(f"Modifier comparison facts are not implemented for {actual.id!r}.")
