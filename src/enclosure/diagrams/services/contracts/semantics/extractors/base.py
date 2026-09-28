from abc import ABC, abstractmethod

from mermaiden.diagrams import domain

from ..model import DiagramContractSemantics


class DiagramSemanticExtractor(ABC):
    kind: str
    order: int

    @abstractmethod
    def extract(self, diagram: domain.DiagramModel) -> DiagramContractSemantics:
        raise NotImplementedError
