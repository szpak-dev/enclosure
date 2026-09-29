from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-realization-attestation")
@dataclass(frozen=True)
class ArchitectureRealizationAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.REALIZATION,
        init=False,
    )
    name: str = field(default="realization", init=False)
    order: int = field(default=30, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return ArchitectureAttestationComponent(kind=self.kind, digest=context.realization.digest)
