from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-schemas-attestation")
@dataclass(frozen=True)
class SchemasAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.SCHEMAS,
        init=False,
    )
    name: str = field(default="schemas", init=False)
    order: int = field(default=60, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return self.component(
            {
                "attestation_schema_version": context.identity.attestation_schema_version,
                "comparison_schema_version": context.comparison.schema_version,
                "contract_schema_version": context.contract.schema_version,
                "implementation_schema_version": context.implementation.schema_version,
            }
        )
