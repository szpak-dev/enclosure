from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, ParameterContractFact
from ..observed.model import ObservedImplementationFact, ObservedParameterFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="parameter-comparison")
@dataclass(frozen=True)
class ParameterComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.PARAMETERS, init=False)
    name: str = field(default="parameters", init=False)
    order: int = field(default=40, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(ParameterContractFact, expected)
        observed = cast(ObservedParameterFact, actual)
        return (
            contract.owner_id == observed.owner_id
            and contract.position == observed.position
            and contract.name == observed.name
            and observed.annotations == (contract.annotation,)
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        identity = cast(ObservedParameterFact, actual).owner_id.removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
