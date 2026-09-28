from dataclasses import dataclass, field
from typing import cast

from wireup import injectable

from ..facts.model import AnnotationContractFact, ArchitectureContractFact, ArchitectureFactCapability
from ..observed.model import ObservedAnnotationFact, ObservedImplementationFact
from .base import ArchitectureComparisonRule


@injectable(as_type=ArchitectureComparisonRule, qualifier="annotation-comparison")
@dataclass(frozen=True)
class AnnotationComparisonRule(ArchitectureComparisonRule):
    capability: ArchitectureFactCapability = field(default=ArchitectureFactCapability.ANNOTATIONS, init=False)
    name: str = field(default="annotations", init=False)
    order: int = field(default=60, init=False)

    def matches(self, expected: ArchitectureContractFact, actual: ObservedImplementationFact) -> bool:
        contract = cast(AnnotationContractFact, expected)
        observed = cast(ObservedAnnotationFact, actual)
        return (
            contract.target_id == observed.target_id
            and contract.role == observed.role
            and contract.expression == observed.expression
        )

    def path(self, actual: ObservedImplementationFact) -> str:
        target_id = cast(ObservedAnnotationFact, actual).target_id
        symbol_id = target_id.removeprefix("parameter:").removeprefix("attribute:")
        identity = symbol_id.removeprefix("symbol:")
        path, _, _ = identity.partition("::")
        return path
