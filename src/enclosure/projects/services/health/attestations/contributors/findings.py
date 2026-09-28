from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-findings-attestation")
@dataclass(frozen=True)
class FindingsAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.FINDINGS,
        init=False,
    )
    name: str = field(default="findings", init=False)
    order: int = field(default=80, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return ArchitectureAttestationComponent(kind=self.kind, digest=context.comparison.digest)
