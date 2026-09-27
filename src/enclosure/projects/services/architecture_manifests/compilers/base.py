from abc import ABC, abstractmethod

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ...architecture_contracts.model import (
    ArchitectureContractDiagram,
    ArchitectureContractUnit,
    ArchitectureDiagramRole,
)
from ..facts.model import ArchitectureContractFact


class ArchitectureDiagramCompiler(ABC):
    role: ArchitectureDiagramRole
    order: int

    @abstractmethod
    def compile(
        self,
        unit: ArchitectureContractUnit,
        diagram: ArchitectureContractDiagram,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureContractFact, ...]:
        raise NotImplementedError
