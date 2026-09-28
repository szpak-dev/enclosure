from dataclasses import dataclass, field

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ....errors import ProjectsError
from ...architecture_contracts.model import (
    ArchitectureContractDiagram,
    ArchitectureContractUnit,
    ArchitectureDiagramRole,
    ArchitectureDiagramScope,
)
from ..facts.model import (
    ArchitectureContractFact,
    ArchitectureDiagramEvidence,
    ArchitectureFactCapability,
    AttributeContractFact,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="entity-manifest")
@dataclass(frozen=True)
class EntityArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.ENTITY, init=False)
    order: int = field(default=30, init=False)

    def compile(
        self,
        unit: ArchitectureContractUnit,
        diagram: ArchitectureContractDiagram,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureContractFact, ...]:
        facts: list[ArchitectureContractFact] = []
        for symbol in semantics.symbols:
            owner_id = f"symbol:{symbol.element_id}"
            facts.extend(
                AttributeContractFact(
                    id=f"attribute:{owner_id}:{member.name}",
                    capability=ArchitectureFactCapability.ATTRIBUTES,
                    required=diagram.scope != ArchitectureDiagramScope.REFERENCE,
                    evidence=(
                        ArchitectureDiagramEvidence(
                            diagram_id=diagram.diagram_id,
                            diagram_revision=diagram.diagram_revision,
                            element_id=symbol.element_id,
                        ),
                    ),
                    owner_id=owner_id,
                    name=member.name,
                    optional=member.type.startswith("Optional[") or member.type.endswith("?"),
                    annotation=member.type,
                    visibility=member.visibility,
                    member_kind=member.modifier,
                )
                for member in symbol.members
                if member.kind == "attribute"
            )
        identities = tuple(fact.id for fact in facts)
        if len(identities) != len(set(identities)):
            raise ProjectsError(f"Entity diagram {diagram.diagram_id!r} declares duplicate attribute identities.")
        return tuple(sorted(facts, key=lambda fact: fact.id))
