from abc import ABC, abstractmethod

from ..evidence.model import ImplementationContext, ImplementationEvidenceSet


class ArchitectureEvidenceProvider(ABC):
    name: str
    order: int

    @abstractmethod
    def collect(self, context: ImplementationContext) -> ImplementationEvidenceSet:
        raise NotImplementedError
