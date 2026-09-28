from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    ArchitectureAttestationComponent,
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
)
from .base import ArchitectureAttestationContributor


@injectable(as_type=ArchitectureAttestationContributor, qualifier="architecture-policies-attestation")
@dataclass(frozen=True)
class PoliciesAttestationContributor(ArchitectureAttestationContributor):
    kind: ArchitectureAttestationEvidenceKind = field(
        default=ArchitectureAttestationEvidenceKind.POLICIES,
        init=False,
    )
    name: str = field(default="policies", init=False)
    order: int = field(default=30, init=False)

    def contribute(self, context: ArchitectureAttestationContext) -> ArchitectureAttestationComponent:
        return self.component(
            {
                "operating_contract": context.operating_contract.model_dump(mode="json"),
                "update_policy": context.update_policy.value,
            }
        )
