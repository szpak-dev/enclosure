from abc import ABC, abstractmethod

from .....errors import ProjectsError
from ....architecture_manifests.facts.model import ArchitectureContractFact
from ....architecture_manifests.model import (
    ArchitectureAssertionResult,
    ArchitectureContractManifest,
    ArchitectureContractManifestUnit,
    ArchitectureSupportState,
)
from ....architecture_manifests.observed.model import ObservedImplementationManifest
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
        contract: ArchitectureContractManifest,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureConformanceFinding:
        raise NotImplementedError

    def expected(
        self,
        result: ArchitectureAssertionResult,
        contract: ArchitectureContractManifest,
    ) -> ArchitectureContractFact:
        matches = tuple(
            fact
            for unit in contract.units
            if unit.key == result.unit_key
            for fact in unit.facts
            if fact.id == result.assertion_id
        )
        if len(matches) != 1:
            raise ProjectsError(f"Architecture assertion {result.assertion_id!r} has no unique expected contract fact.")
        return matches[0]

    def unit(
        self,
        result: ArchitectureAssertionResult,
        contract: ArchitectureContractManifest,
    ) -> ArchitectureContractManifestUnit:
        matches = tuple(unit for unit in contract.units if unit.key == result.unit_key)
        if len(matches) != 1:
            raise ProjectsError(f"Architecture assertion {result.assertion_id!r} has no unique contract unit.")
        return matches[0]

    def support(
        self,
        result: ArchitectureAssertionResult,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureSupportState:
        matches = tuple(item.support for item in observed.capabilities if item.capability == result.capability)
        if len(matches) != 1:
            raise ProjectsError(
                f"Architecture capability {result.capability.value!r} has no unique support declaration."
            )
        return matches[0]
