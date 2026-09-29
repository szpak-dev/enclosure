from abc import ABC, abstractmethod

from ..evidence.model import ImplementationEvidenceSet, ProviderManifest


class ImplementationSemanticTranslator(ABC):
    provider: str
    language: str
    order: int

    @abstractmethod
    def translate(self, manifest: ProviderManifest) -> ImplementationEvidenceSet:
        raise NotImplementedError
