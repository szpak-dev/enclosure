from dataclasses import dataclass, field

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics, DiagramContractType

from ....errors import ProjectsError
from ...architecture_contracts.model import (
    ArchitectureContractDiagram,
    ArchitectureContractUnit,
    ArchitectureDiagramRole,
    ArchitectureDiagramScope,
)
from ..assertions.model import (
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    ArchitectureCardinality,
    ArchitectureDiagramEvidence,
    ArchitectureEntityKey,
    ArchitectureRelationshipKind,
    ArchitectureTypeReference,
    EntityAssertion,
    EntityFieldAssertion,
    RelationshipAssertion,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="entity-manifest")
@dataclass(frozen=True)
class EntityArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.ENTITY, init=False)
    order: int = field(default=30, init=False)

    def type_reference(self, value: DiagramContractType) -> ArchitectureTypeReference:
        return ArchitectureTypeReference(
            name=value.name,
            arguments=tuple(self.type_reference(argument) for argument in value.arguments),
            cardinality=ArchitectureCardinality(value.cardinality.value),
        )

    def entity_key(self, value: str) -> ArchitectureEntityKey:
        normalized = value.casefold()
        keys = {
            "pk": ArchitectureEntityKey.PRIMARY,
            "primary": ArchitectureEntityKey.PRIMARY,
            "fk": ArchitectureEntityKey.FOREIGN,
            "foreign": ArchitectureEntityKey.FOREIGN,
            "uk": ArchitectureEntityKey.UNIQUE,
            "unique": ArchitectureEntityKey.UNIQUE,
        }
        if normalized not in keys:
            raise ProjectsError(f"Entity key {value!r} has no language-neutral architecture meaning.")
        return keys[normalized]

    def compile(
        self,
        unit: ArchitectureContractUnit,
        diagram: ArchitectureContractDiagram,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureAssertion, ...]:
        assertions: list[ArchitectureAssertion] = []
        required = diagram.scope != ArchitectureDiagramScope.REFERENCE
        symbols = {symbol.element_id: symbol for symbol in semantics.symbols}
        for symbol in semantics.symbols:
            owner_id = f"entity:{symbol.element_id}"
            evidence = (
                ArchitectureDiagramEvidence(
                    diagram_id=diagram.diagram_id,
                    diagram_revision=diagram.diagram_revision,
                    element_id=symbol.element_id,
                ),
            )
            assertions.append(
                EntityAssertion(
                    id=owner_id,
                    unit_key=unit.key,
                    subject_id=owner_id,
                    kind=ArchitectureAssertionKind.ENTITY,
                    required=required,
                    evidence=evidence,
                    name=symbol.label,
                )
            )
            assertions.extend(
                EntityFieldAssertion(
                    id=f"entity-field:{symbol.element_id}:{member.name}",
                    unit_key=unit.key,
                    subject_id=f"entity-field:{symbol.element_id}:{member.name}",
                    kind=ArchitectureAssertionKind.ENTITY_FIELD,
                    required=required,
                    evidence=evidence,
                    owner_id=owner_id,
                    name=member.name,
                    type=self.type_reference(member.type),
                    keys=tuple(self.entity_key(key) for key in member.keys),
                    cardinality=ArchitectureCardinality(member.cardinality.value),
                )
                for member in symbol.members
                if member.kind == "attribute"
            )
        for relation in semantics.relations:
            if relation.source_id not in symbols or relation.target_id not in symbols:
                raise ProjectsError(f"Entity relation {relation.id!r} references an undeclared entity.")
            relation_id = f"relationship:{relation.id}"
            assertions.append(
                RelationshipAssertion(
                    id=relation_id,
                    unit_key=unit.key,
                    subject_id=relation_id,
                    kind=ArchitectureAssertionKind.RELATIONSHIP,
                    required=required,
                    evidence=(
                        ArchitectureDiagramEvidence(
                            diagram_id=diagram.diagram_id,
                            diagram_revision=diagram.diagram_revision,
                            element_id=relation.id,
                        ),
                    ),
                    source_id=f"entity:{relation.source_id}",
                    target_id=f"entity:{relation.target_id}",
                    relationship_kind=(
                        ArchitectureRelationshipKind.IDENTIFYING
                        if relation.identifying
                        else ArchitectureRelationshipKind.NON_IDENTIFYING
                    ),
                    source_cardinality=ArchitectureCardinality(relation.source_cardinality.value),
                    target_cardinality=ArchitectureCardinality(relation.target_cardinality.value),
                )
            )
        identities = tuple(assertion.id for assertion in assertions)
        if len(identities) != len(set(identities)):
            raise ProjectsError(f"Entity diagram {diagram.diagram_id!r} declares duplicate architecture assertions.")
        return tuple(sorted(assertions, key=lambda assertion: (assertion.kind.value, assertion.id)))
