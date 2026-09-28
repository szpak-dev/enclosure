from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-configuration-attestation")
@dataclass(frozen=True)
class ConfigurationAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.CONFIGURATION,
        init=False,
    )
    name: str = field(default="configuration", init=False)
    order: int = field(default=40, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return ArchitectureAttestationComponent(kind=self.kind, digest=context.configuration_revision)
