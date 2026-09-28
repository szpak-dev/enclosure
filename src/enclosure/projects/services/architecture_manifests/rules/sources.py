from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import ArchitectureContractFact, ArchitectureFactCapability, SourceContractFact
from ..observed.model import ObservedImplementationFact, ObservedSourceFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="source-comparison")
@dataclass(frozen=True)
class SourceComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.SOURCES, init=False)
    name: str = field(default="sources", init=False)
    order: int = field(default=10, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        return cast(SourceContractFact, expected).path == cast(ObservedSourceFact, actual).path

    def path(self, actual: ObservedImplementationFact) -> str:
        return cast(ObservedSourceFact, actual).path
