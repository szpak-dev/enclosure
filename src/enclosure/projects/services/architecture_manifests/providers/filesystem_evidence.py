from dataclasses import dataclass, field

from wireup import injectable

from ..assertions.model import ArchitectureAssertionKind
from ..evidence.model import (
    ArchitectureSupportState,
    ArtifactEvidence,
    EvidenceCapability,
    EvidenceProviderReceipt,
    EvidenceSupport,
    ImplementationContext,
    ImplementationEvidence,
    ImplementationEvidenceSet,
    ImplementationLocator,
)
from .base import ArchitectureEvidenceProvider


@injectable(as_type=ArchitectureEvidenceProvider, qualifier="filesystem-evidence")
@dataclass(frozen=True)
class FilesystemArtifactEvidenceProvider(ArchitectureEvidenceProvider):
    name: str = field(default="filesystem", init=False)
    order: int = field(default=10, init=False)

    def collect(self, context: ImplementationContext) -> ImplementationEvidenceSet:
        artifact_support = context.artifact_inventory.support
        observations = tuple(
            observation for observation in context.artifact_inventory.observations if observation.exists
        )
        evidence: tuple[ImplementationEvidence, ...] = tuple(
            ArtifactEvidence(
                id=f"filesystem:{observation.artifact_kind.value}:{observation.path}",
                kind=ArchitectureAssertionKind.ARTIFACT,
                locator=ImplementationLocator(
                    provider=self.name,
                    coordinate=observation.path,
                    path=observation.path,
                ),
                reference=observation.path,
                path=observation.path,
                artifact_kind=observation.artifact_kind,
                content_digest=observation.content_digest,
            )
            for observation in observations
        )
        capabilities = tuple(
            EvidenceCapability(
                kind=kind,
                semantics=EvidenceSupport(
                    support=(
                        artifact_support
                        if kind == ArchitectureAssertionKind.ARTIFACT
                        else ArchitectureSupportState.UNSUPPORTED
                    ),
                    explanation=(
                        ""
                        if kind == ArchitectureAssertionKind.ARTIFACT
                        and artifact_support == ArchitectureSupportState.SUPPORTED
                        else "The filesystem provider only observes supplied artifact paths."
                    ),
                ),
                inventory=EvidenceSupport(
                    support=(
                        artifact_support
                        if kind == ArchitectureAssertionKind.ARTIFACT
                        else ArchitectureSupportState.UNSUPPORTED
                    ),
                    explanation=(
                        ""
                        if kind == ArchitectureAssertionKind.ARTIFACT
                        and artifact_support == ArchitectureSupportState.SUPPORTED
                        else "The filesystem provider only inventories supplied artifact paths."
                    ),
                ),
            )
            for kind in ArchitectureAssertionKind
        )
        return ImplementationEvidenceSet(
            receipt=EvidenceProviderReceipt(
                provider=self.name,
                version="1",
                language="filesystem",
                source_digest=(
                    context.artifact_inventory.digest
                    if artifact_support != ArchitectureSupportState.UNSUPPORTED
                    else ""
                ),
                capabilities=capabilities,
            ),
            evidence=evidence,
        )
