from dataclasses import dataclass, field
from pathlib import PurePosixPath

from wireup import injectable

from ..assertions.model import ArchitectureArtifactKind, ArchitectureAssertionKind
from ..evidence.model import (
    ArchitectureSupportState,
    ArtifactEvidence,
    EvidenceCapability,
    EvidenceProviderReceipt,
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
        paths = tuple(sorted(set(context.artifact_paths)))
        directories = {str(parent) for path in paths for parent in PurePosixPath(path).parents if str(parent) != "."}
        evidence: list[ImplementationEvidence] = []
        evidence.extend(
            ArtifactEvidence(
                id=f"filesystem:directory:{path}",
                kind=ArchitectureAssertionKind.ARTIFACT,
                locator=ImplementationLocator(provider=self.name, coordinate=path, path=path),
                reference=path,
                path=path,
                artifact_kind=ArchitectureArtifactKind.DIRECTORY,
                content_digest="",
            )
            for path in sorted(directories)
        )
        evidence.extend(
            ArtifactEvidence(
                id=f"filesystem:file:{path}",
                kind=ArchitectureAssertionKind.ARTIFACT,
                locator=ImplementationLocator(provider=self.name, coordinate=path, path=path),
                reference=path,
                path=path,
                artifact_kind=ArchitectureArtifactKind.FILE,
                content_digest="",
            )
            for path in paths
        )
        capabilities = tuple(
            EvidenceCapability(
                kind=kind,
                support=(
                    ArchitectureSupportState.SUPPORTED
                    if kind == ArchitectureAssertionKind.ARTIFACT and paths
                    else ArchitectureSupportState.UNSUPPORTED
                ),
                explanation=(
                    ""
                    if kind == ArchitectureAssertionKind.ARTIFACT and paths
                    else "The filesystem provider only observes supplied artifact paths."
                ),
            )
            for kind in ArchitectureAssertionKind
        )
        return ImplementationEvidenceSet(
            receipt=EvidenceProviderReceipt(
                provider=self.name,
                version="1",
                language="filesystem",
                source_digest="",
                capabilities=capabilities,
            ),
            evidence=tuple(evidence),
        )
