from dataclasses import dataclass, field
from typing import cast

import mermaiden.diagrams.classdiagram.diagram
from mermaiden.diagrams import domain
from mermaiden.diagrams.classdiagram.elements import Class
from mermaiden.diagrams.classdiagram.relations import ClassRelation
from mermaiden.diagrams.classdiagram.values.members import ClassType
from wireup import injectable

from ..model import (
    DiagramContractMember,
    DiagramContractParameter,
    DiagramContractRelation,
    DiagramContractSemantics,
    DiagramContractSymbol,
)
from .base import DiagramSemanticExtractor


@injectable(as_type=DiagramSemanticExtractor, qualifier="class-contract")
@dataclass(frozen=True)
class ClassDiagramSemanticExtractor(DiagramSemanticExtractor):
    kind: str = field(default="classDiagram", init=False)
    order: int = field(default=20, init=False)

    def type_name(self, value: ClassType) -> str:
        if not value.arguments:
            return value.name
        return f"{value.name}[{self.type_name(value.arguments[0])}]"

    def extract(self, diagram: domain.DiagramModel) -> DiagramContractSemantics:
        class_model = cast(mermaiden.diagrams.classdiagram.diagram.ClassDiagram, diagram)
        classes = tuple(cast(Class, element) for element in class_model.walk_elements("") if element.kind == "class")
        symbols: list[DiagramContractSymbol] = []
        for class_value in classes:
            members = [
                DiagramContractMember(
                    name=attribute.name,
                    kind="attribute",
                    type=self.type_name(attribute.type),
                    visibility=attribute.visibility.value,
                    modifier="static" if attribute.static else "instance",
                    parameters=(),
                )
                for attribute in class_value.attributes
            ]
            members.extend(
                DiagramContractMember(
                    name=method.name,
                    kind="method",
                    type=self.type_name(method.return_type),
                    visibility=method.visibility.value,
                    modifier=method.modifier.value,
                    parameters=tuple(
                        DiagramContractParameter(
                            name=parameter.name,
                            type=self.type_name(parameter.type),
                            position=position,
                        )
                        for position, parameter in enumerate(method.parameters)
                    ),
                )
                for method in class_value.methods
            )
            symbols.append(
                DiagramContractSymbol(
                    element_id=class_value.id,
                    label=class_value.label,
                    kind="class",
                    annotations=class_value.annotations,
                    members=tuple(sorted(members, key=lambda item: (item.kind, item.name, item.type))),
                )
            )
        relations = tuple(
            DiagramContractRelation(
                id=relation.id,
                source_id=relation.source_id,
                target_id=relation.target_id,
                kind=relation.relation_kind.value,
                label=relation.label,
            )
            for relation in (cast(ClassRelation, item) for item in class_model.find_relations(""))
        )
        return DiagramContractSemantics(
            kind=self.kind,
            paths=(),
            symbols=tuple(sorted(symbols, key=lambda item: item.element_id)),
            relations=tuple(sorted(relations, key=lambda item: item.id)),
        )
