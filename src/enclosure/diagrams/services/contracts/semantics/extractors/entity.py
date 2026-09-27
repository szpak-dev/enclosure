from dataclasses import dataclass, field
from typing import cast

from mermaiden.diagrams.domain import DiagramModel
from mermaiden.diagrams.er.diagram import EntityRelationshipDiagram
from mermaiden.diagrams.er.elements import Entity, EntityAttribute
from mermaiden.diagrams.er.relations import EntityRelationship
from wireup import injectable

from ..model import DiagramContractMember, DiagramContractRelation, DiagramContractSemantics, DiagramContractSymbol
from .base import DiagramSemanticExtractor


@injectable(as_type=DiagramSemanticExtractor, qualifier="entity-contract")
@dataclass(frozen=True)
class EntitySemanticExtractor(DiagramSemanticExtractor):
    kind: str = field(default="erDiagram", init=False)
    order: int = field(default=30, init=False)

    def extract(self, diagram: DiagramModel) -> DiagramContractSemantics:
        entity_diagram = cast(EntityRelationshipDiagram, diagram)
        entities = tuple(cast(Entity, element) for element in entity_diagram.root_elements if element.kind == "entity")
        symbols = tuple(
            DiagramContractSymbol(
                element_id=entity.id,
                label=entity.label,
                kind="entity",
                annotations=(),
                members=tuple(
                    DiagramContractMember(
                        name=attribute.label,
                        kind="attribute",
                        type=attribute.data_type,
                        visibility="public",
                        modifier="instance",
                        parameters=(),
                    )
                    for attribute in (cast(EntityAttribute, item) for item in entity.elements)
                ),
            )
            for entity in entities
        )
        relations = tuple(
            DiagramContractRelation(
                id=relation.id,
                source_id=relation.source_id,
                target_id=relation.target_id,
                kind="identifying" if relation.identifying else "non_identifying",
                label="",
            )
            for relation in (cast(EntityRelationship, item) for item in entity_diagram.find_relations(""))
        )
        return DiagramContractSemantics(
            kind=self.kind,
            paths=(),
            symbols=tuple(sorted(symbols, key=lambda item: item.element_id)),
            relations=tuple(sorted(relations, key=lambda item: item.id)),
        )
