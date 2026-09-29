from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-evidence-attestation")
@dataclass(frozen=True)
class ImplementationEvidenceAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.IMPLEMENTATION_EVIDENCE,
        init=False,
    )
    name: str = field(default="implementation-evidence", init=False)
    order: int = field(default=20, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return ArchitectureAttestationComponent(kind=self.kind, digest=context.implementation.digest)
