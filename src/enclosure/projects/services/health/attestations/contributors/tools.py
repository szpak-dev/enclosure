from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-tools-attestation")
@dataclass(frozen=True)
class ToolsAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.TOOLS,
        init=False,
    )
    name: str = field(default="tools", init=False)
    order: int = field(default=60, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return self.component(
            {
                "conformance_producer": context.identity.producer,
                "conformance_producer_revision": context.identity.producer_revision,
                "extractor_id": context.observed.extractor_id,
                "language": context.observed.language,
                "modwire_version": context.observed.modwire_version,
            }
        )
