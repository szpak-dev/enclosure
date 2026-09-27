from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, CallableContractFact
from ..observed.model import ObservedCallableFact, ObservedImplementationFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="callable-comparison")
@dataclass(frozen=True)
class CallableComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.CALLABLES, init=False)
    name: str = field(default="callables", init=False)
    order: int = field(default=30, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(CallableContractFact, expected)
        observed = cast(ObservedCallableFact, actual)
        return contract.owner_id == observed.owner_id and contract.callable_kind == observed.callable_kind

    def path(self, actual: ObservedImplementationFact) -> str:
        identity = cast(ObservedCallableFact, actual).owner_id.removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
