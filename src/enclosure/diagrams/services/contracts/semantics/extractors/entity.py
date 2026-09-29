from dataclasses import dataclass, field
from typing import cast

import mermaiden.diagrams.er.diagram
from mermaiden.diagrams import domain
from mermaiden.diagrams.er.elements import Entity, EntityAttribute
from mermaiden.diagrams.er.relations import EntityRelationship
from wireup import injectable

from ..model import (
    DiagramContractCardinality,
    DiagramContractMember,
    DiagramContractRelation,
    DiagramContractSemantics,
    DiagramContractSymbol,
    DiagramContractType,
)
from .base import DiagramSemanticExtractor


@injectable(as_type=DiagramSemanticExtractor, qualifier="entity-contract")
@dataclass(frozen=True)
class EntitySemanticExtractor(DiagramSemanticExtractor):
    kind: str = field(default="erDiagram", init=False)
    order: int = field(default=30, init=False)

    def cardinality(self, value: str) -> DiagramContractCardinality:
        return {
            "zero_or_one": DiagramContractCardinality.OPTIONAL,
            "exactly_one": DiagramContractCardinality.ONE,
            "zero_or_more": DiagramContractCardinality.MANY,
            "one_or_more": DiagramContractCardinality.NONEMPTY_MANY,
        }[value]

    def contract_type(self, value: str) -> DiagramContractType:
        optional = value.endswith("?")
        return DiagramContractType(
            name=value.removesuffix("?"),
            arguments=(),
            cardinality=(
                DiagramContractCardinality.OPTIONAL if optional else DiagramContractCardinality.ONE
            ),
        )

    def extract(self, diagram: domain.DiagramModel) -> DiagramContractSemantics:
        entity_diagram = cast(mermaiden.diagrams.er.diagram.EntityRelationshipDiagram, diagram)
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
                        type=self.contract_type(attribute.data_type),
                        visibility="public",
                        modifier="instance",
                        parameters=(),
                        keys=tuple(sorted(attribute.keys)),
                        cardinality=(
                            DiagramContractCardinality.OPTIONAL
                            if attribute.data_type.endswith("?")
                            else DiagramContractCardinality.ONE
                        ),
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
                label=relation.label,
                source_cardinality=self.cardinality(relation.source_cardinality.value),
                target_cardinality=self.cardinality(relation.target_cardinality.value),
                identifying=relation.identifying,
            )
            for relation in (cast(EntityRelationship, item) for item in entity_diagram.find_relations(""))
        )
        return DiagramContractSemantics(
            kind=self.kind,
            paths=(),
            symbols=tuple(sorted(symbols, key=lambda item: item.element_id)),
            relations=tuple(sorted(relations, key=lambda item: item.id)),
        )
