from abc import ABC, abstractmethod

from ..evidence.model import (
    ArtifactObservationManifest,
    ArtifactObservationPlan,
    ImplementationContext,
    ImplementationEvidenceSet,
)
from ..model import ArchitectureContractManifest


class ArchitectureArtifactObserver(ABC):
    @abstractmethod
    def plan(self, contract: ArchitectureContractManifest) -> ArtifactObservationPlan:
        raise NotImplementedError

    @abstractmethod
    def observe(self, root: str, plan: ArtifactObservationPlan) -> ArtifactObservationManifest:
        raise NotImplementedError

    @abstractmethod
    def verify(self, root: str, plan: ArtifactObservationPlan, expected_digest: str) -> None:
        raise NotImplementedError


class ArchitectureEvidenceProvider(ABC):
    name: str
    order: int

    @abstractmethod
    def collect(self, context: ImplementationContext) -> ImplementationEvidenceSet:
        raise NotImplementedError
