import json
from abc import ABC, abstractmethod
from hashlib import sha256

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)


class ArchitectureAttestationContributor(ABC):
    kind: ArchitectureAttestationEvidenceKind
    name: str
    order: int

    @abstractmethod
    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        raise NotImplementedError

    def component(self, value: object) -> ArchitectureAttestationComponent:
        canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureAttestationComponent(
            kind=self.kind,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )
