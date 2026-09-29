from abc import ABC, abstractmethod

from ....architecture_manifests.model import (
    ArchitectureAssertionResult,
    ArchitectureFindingOwner,
)
from ..model import ArchitectureConformanceFinding


class ArchitectureConformanceFindingProjector(ABC):
    name: str
    order: int

    @abstractmethod
    def supports(self, result: ArchitectureAssertionResult) -> bool:
        raise NotImplementedError

    @abstractmethod
    def project(
        self,
        result: ArchitectureAssertionResult,
    ) -> ArchitectureConformanceFinding:
        raise NotImplementedError

    def next_action(self, owner: ArchitectureFindingOwner, target: str) -> str:
        if owner == ArchitectureFindingOwner.CONTRACT:
            return f"Correct the accepted architectural intent for {target}."
        if owner == ArchitectureFindingOwner.REALIZATION:
            return f"Clarify the intent-to-implementation realization for {target}."
        if owner == ArchitectureFindingOwner.IMPLEMENTATION:
            return f"Align the implementation of {target} with accepted architectural intent."
        return f"Provide complete canonical implementation evidence for {target}."
