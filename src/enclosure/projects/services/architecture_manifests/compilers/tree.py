from dataclasses import dataclass, field
from pathlib import PurePosixPath

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ....errors import ProjectsError
from ...architecture_contracts.model import (
    ArchitectureContractDiagram,
    ArchitectureContractUnit,
    ArchitectureDiagramRole,
)
from ..facts.model import (
    ArchitectureContractFact,
    ArchitectureDiagramEvidence,
    ArchitectureFactCapability,
    SourceContractFact,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="tree-manifest")
@dataclass(frozen=True)
class TreeArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.TREE, init=False)
    order: int = field(default=10, init=False)

    def compile(
        self,
        unit: ArchitectureContractUnit,
        diagram: ArchitectureContractDiagram,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureContractFact, ...]:
        facts: list[ArchitectureContractFact] = []
        for path in semantics.paths:
            parsed = PurePosixPath(path.path)
            normalized = str(parsed)
            if parsed.is_absolute() or ".." in parsed.parts or normalized != path.path:
                raise ProjectsError(f"Tree path {path.path!r} must be normalized and project-relative.")
            if path.kind == "file":
                if (
                    unit.source_root != "."
                    and normalized != unit.source_root
                    and not normalized.startswith(f"{unit.source_root}/")
                ):
                    raise ProjectsError(
                        f"Tree source {normalized!r} is outside contract source root {unit.source_root!r}."
                    )
                facts.append(
                    SourceContractFact(
                        id=f"source:{normalized}",
                        capability=ArchitectureFactCapability.SOURCES,
                        required=True,
                        evidence=(
                            ArchitectureDiagramEvidence(
                                diagram_id=diagram.diagram_id,
                                diagram_revision=diagram.diagram_revision,
                                element_id=path.element_id,
                            ),
                        ),
                        path=normalized,
                    )
                )
        identities = tuple(fact.id for fact in facts)
        if len(identities) != len(set(identities)):
            raise ProjectsError(f"Tree diagram {diagram.diagram_id!r} declares duplicate source identities.")
        return tuple(sorted(facts, key=lambda fact: fact.id))
