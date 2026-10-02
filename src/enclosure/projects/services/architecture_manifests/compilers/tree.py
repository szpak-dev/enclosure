from dataclasses import dataclass, field
from pathlib import PurePosixPath

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ....errors import ProjectsError
from ...architecture_contracts.model import (
    ArchitectureContractDiagramContract,
    ArchitectureContractUnitContract,
    ArchitectureDiagramRole,
    ArchitectureDiagramScope,
)
from ..assertions.model import (
    ArchitectureArtifactKind,
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    ArchitectureDiagramEvidence,
    ArtifactAssertion,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="tree-manifest")
@dataclass(frozen=True)
class TreeArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.TREE, init=False)
    order: int = field(default=10, init=False)

    def compile(
        self,
        unit: ArchitectureContractUnitContract,
        diagram: ArchitectureContractDiagramContract,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureAssertion, ...]:
        assertions: list[ArchitectureAssertion] = []
        for path in semantics.paths:
            parsed = PurePosixPath(path.path)
            normalized = str(parsed)
            if parsed.is_absolute() or ".." in parsed.parts or normalized != path.path:
                raise ProjectsError(f"Tree path {path.path!r} must be normalized and project-relative.")
            if (
                unit.source_root != "."
                and normalized != unit.source_root
                and not normalized.startswith(f"{unit.source_root}/")
            ):
                continue
            subject_id = f"artifact:{path.element_id}"
            assertions.append(
                ArtifactAssertion(
                    id=subject_id,
                    unit_key=unit.key,
                    subject_id=subject_id,
                    kind=ArchitectureAssertionKind.ARTIFACT,
                    required=diagram.scope != ArchitectureDiagramScope.REFERENCE,
                    evidence=(
                        ArchitectureDiagramEvidence(
                            diagram_id=diagram.diagram_id,
                            diagram_revision=diagram.diagram_revision,
                            element_id=path.element_id,
                        ),
                    ),
                    path=normalized,
                    artifact_kind=ArchitectureArtifactKind(path.kind),
                )
            )
        identities = tuple(assertion.id for assertion in assertions)
        if len(identities) != len(set(identities)):
            raise ProjectsError(f"Tree diagram {diagram.diagram_id!r} declares duplicate artifact identities.")
        return tuple(sorted(assertions, key=lambda assertion: assertion.id))
