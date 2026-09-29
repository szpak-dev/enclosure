from dataclasses import dataclass, field
from typing import cast

import mermaiden.diagrams.classdiagram.diagram
from mermaiden.diagrams import domain
from mermaiden.diagrams.classdiagram.elements import Class
from mermaiden.diagrams.classdiagram.relations import ClassRelation
from mermaiden.diagrams.classdiagram.values.members import ClassType
from wireup import injectable

from ..model import (
    DiagramContractCardinality,
    DiagramContractMember,
    DiagramContractParameter,
    DiagramContractRelation,
    DiagramContractSemantics,
    DiagramContractSymbol,
    DiagramContractType,
)
from .base import DiagramSemanticExtractor


@injectable(as_type=DiagramSemanticExtractor, qualifier="class-contract")
@dataclass(frozen=True)
class ClassDiagramSemanticExtractor(DiagramSemanticExtractor):
    kind: str = field(default="classDiagram", init=False)
    order: int = field(default=20, init=False)

    def contract_type(self, value: ClassType) -> DiagramContractType:
        return DiagramContractType(
            name=value.name,
            arguments=tuple(self.contract_type(argument) for argument in value.arguments),
            cardinality=DiagramContractCardinality.ONE,
        )

    def extract(self, diagram: domain.DiagramModel) -> DiagramContractSemantics:
        class_model = cast(mermaiden.diagrams.classdiagram.diagram.ClassDiagram, diagram)
        classes = tuple(cast(Class, element) for element in class_model.walk_elements("") if element.kind == "class")
        symbols: list[DiagramContractSymbol] = []
        for class_value in classes:
            members = [
                DiagramContractMember(
                    name=attribute.name,
                    kind="attribute",
                    type=self.contract_type(attribute.type),
                    visibility=attribute.visibility.value,
                    modifier="static" if attribute.static else "instance",
                    parameters=(),
                    keys=(),
                    cardinality=DiagramContractCardinality.ONE,
                )
                for attribute in class_value.attributes
            ]
            members.extend(
                DiagramContractMember(
                    name=method.name,
                    kind="method",
                    type=self.contract_type(method.return_type),
                    visibility=method.visibility.value,
                    modifier=method.modifier.value,
                    parameters=tuple(
                        DiagramContractParameter(
                            name=parameter.name,
                            type=self.contract_type(parameter.type),
                            position=position,
                        )
                        for position, parameter in enumerate(method.parameters)
                    ),
                    keys=(),
                    cardinality=DiagramContractCardinality.ONE,
                )
                for method in class_value.methods
            )
            symbols.append(
                DiagramContractSymbol(
                    element_id=class_value.id,
                    label=class_value.label,
                    kind="class",
                    annotations=class_value.annotations,
                    members=tuple(sorted(members, key=lambda item: (item.kind, item.name))),
                )
            )
        relations = tuple(
            DiagramContractRelation(
                id=relation.id,
                source_id=relation.source_id,
                target_id=relation.target_id,
                kind=relation.relation_kind.value,
                label=relation.label,
                source_cardinality=DiagramContractCardinality.ONE,
                target_cardinality=DiagramContractCardinality.ONE,
                identifying=False,
            )
            for relation in (cast(ClassRelation, item) for item in class_model.find_relations(""))
        )
        return DiagramContractSemantics(
            kind=self.kind,
            paths=(),
            symbols=tuple(sorted(symbols, key=lambda item: item.element_id)),
            relations=tuple(sorted(relations, key=lambda item: item.id)),
        )
