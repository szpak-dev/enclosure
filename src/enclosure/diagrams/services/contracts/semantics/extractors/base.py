from abc import ABC, abstractmethod

from mermaiden.diagrams.domain import DiagramModel

from ..model import DiagramContractSemantics


class DiagramSemanticExtractor(ABC):
    kind: str
    order: int

    @abstractmethod
    def extract(self, diagram: DiagramModel) -> DiagramContractSemantics:
        raise NotImplementedError
