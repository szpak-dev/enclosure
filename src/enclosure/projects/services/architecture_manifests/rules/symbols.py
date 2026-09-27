from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, SymbolContractFact
from ..observed.model import ObservedImplementationFact, ObservedSymbolFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="symbol-comparison")
@dataclass(frozen=True)
class SymbolComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.SYMBOLS, init=False)
    name: str = field(default="symbols", init=False)
    order: int = field(default=20, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(SymbolContractFact, expected)
        observed = cast(ObservedSymbolFact, actual)
        return (
            contract.path == observed.path
            and contract.family == observed.family
            and contract.qualified_name == observed.qualified_name
            and contract.kind == observed.kind
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        return cast(ObservedSymbolFact, actual).path
