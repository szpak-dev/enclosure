from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, DependencyContractFact
from ..observed.model import ObservedDependencyFact, ObservedImplementationFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="dependency-comparison")
@dataclass(frozen=True)
class DependencyComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.DEPENDENCIES, init=False)
    name: str = field(default="dependencies", init=False)
    order: int = field(default=80, init=False)

    def governs(self, actual: ObservedImplementationFact) -> bool:
        dependency = cast(ObservedDependencyFact, actual)
        return dependency.target_kind == "source" and dependency.resolution == "resolved"

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(DependencyContractFact, expected)
        observed = cast(ObservedDependencyFact, actual)
        return (
            contract.source_path == observed.source_path
            and contract.kind == observed.kind
            and contract.target == observed.target
            and contract.specifier == observed.specifier
            and contract.resolution == observed.resolution
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        return cast(ObservedDependencyFact, actual).source_path
