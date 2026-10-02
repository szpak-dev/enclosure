from abc import ABC, abstractmethod

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ...architecture_contracts.model import (
    ArchitectureContractDiagramContract,
    ArchitectureContractUnitContract,
    ArchitectureDiagramRole,
)
from ..assertions.model import ArchitectureAssertion


class ArchitectureDiagramCompiler(ABC):
    role: ArchitectureDiagramRole
    order: int

    @abstractmethod
    def compile(
        self,
        unit: ArchitectureContractUnitContract,
        diagram: ArchitectureContractDiagramContract,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureAssertion, ...]:
        raise NotImplementedError
