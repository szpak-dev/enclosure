from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-source-attestation")
@dataclass(frozen=True)
class SourceAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.SOURCE,
        init=False,
    )
    name: str = field(default="source", init=False)
    order: int = field(default=20, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return ArchitectureAttestationComponent(kind=self.kind, digest=context.observed.source_digest)
