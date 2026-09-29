from dataclasses import dataclass, field

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import (
    DiagramContractSemantics,
    DiagramContractType,
)

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
    ArchitectureClassifierKind,
    ArchitectureDiagramEvidence,
    ArchitectureMemberKind,
    ArchitectureMemberOwnership,
    ArchitectureParameter,
    ArchitectureRelationshipKind,
    ArchitectureTypeReference,
    ArchitectureVisibility,
    ClassifierAssertion,
    MemberAssertion,
    RelationshipAssertion,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="uml-manifest")
@dataclass(frozen=True)
class UmlArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.UML, init=False)
    order: int = field(default=20, init=False)

    def type_reference(self, value: DiagramContractType) -> ArchitectureTypeReference:
        normalized_name = value.name.casefold()
        cardinality = ArchitectureCardinality(value.cardinality.value)
        arguments = tuple(self.type_reference(argument) for argument in value.arguments)
        if normalized_name == "optional" and len(arguments) == 1:
            inner = arguments[0]
            return inner.model_copy(update={"cardinality": ArchitectureCardinality.OPTIONAL})
        if normalized_name == "collection" and len(arguments) == 1:
            inner = arguments[0]
            return inner.model_copy(update={"cardinality": ArchitectureCardinality.MANY})
        return ArchitectureTypeReference(name=value.name, arguments=arguments, cardinality=cardinality)

    def classifier_kind(self, annotations: tuple[str, ...]) -> ArchitectureClassifierKind:
        normalized = {annotation.casefold() for annotation in annotations}
        if "interface" in normalized:
            return ArchitectureClassifierKind.INTERFACE
        if "enumeration" in normalized or "enum" in normalized:
            return ArchitectureClassifierKind.ENUMERATION
        return ArchitectureClassifierKind.CLASS

    def relationship_kind(self, value: str) -> ArchitectureRelationshipKind:
        return {
            "association": ArchitectureRelationshipKind.ASSOCIATION,
            "inheritance": ArchitectureRelationshipKind.GENERALIZATION,
            "composition": ArchitectureRelationshipKind.COMPOSITION,
            "aggregation": ArchitectureRelationshipKind.AGGREGATION,
            "dependency": ArchitectureRelationshipKind.DEPENDENCY,
            "realization": ArchitectureRelationshipKind.REALIZATION,
        }[value]

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
            subject_id = f"classifier:{symbol.element_id}"
            evidence = (
                ArchitectureDiagramEvidence(
                    diagram_id=diagram.diagram_id,
                    diagram_revision=diagram.diagram_revision,
                    element_id=symbol.element_id,
                ),
            )
            assertions.append(
                ClassifierAssertion(
                    id=subject_id,
                    unit_key=unit.key,
                    subject_id=subject_id,
                    kind=ArchitectureAssertionKind.CLASSIFIER,
                    required=required,
                    evidence=evidence,
                    name=symbol.label,
                    classifier_kind=self.classifier_kind(symbol.annotations),
                    abstract="abstract" in {annotation.casefold() for annotation in symbol.annotations},
                )
            )
            for member in symbol.members:
                member_kind = (
                    ArchitectureMemberKind.PROPERTY
                    if member.kind == "attribute"
                    else ArchitectureMemberKind.OPERATION
                )
                member_id = f"member:{symbol.element_id}:{member_kind.value}:{member.name}"
                assertions.append(
                    MemberAssertion(
                        id=member_id,
                        unit_key=unit.key,
                        subject_id=member_id,
                        kind=ArchitectureAssertionKind.MEMBER,
                        required=required,
                        evidence=evidence,
                        owner_id=subject_id,
                        name=member.name,
                        member_kind=member_kind,
                        type=self.type_reference(member.type),
                        visibility=ArchitectureVisibility(member.visibility),
                        ownership=(
                            ArchitectureMemberOwnership.TYPE
                            if member.modifier == "static"
                            else ArchitectureMemberOwnership.INSTANCE
                        ),
                        abstract=member.modifier == "abstract",
                        parameters=tuple(
                            ArchitectureParameter(
                                name=parameter.name,
                                position=parameter.position,
                                type=self.type_reference(parameter.type),
                            )
                            for parameter in member.parameters
                        ),
                    )
                )
        for relation in semantics.relations:
            if relation.source_id not in symbols or relation.target_id not in symbols:
                raise ProjectsError(f"UML relation {relation.id!r} references an undeclared classifier.")
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
                    source_id=f"classifier:{relation.source_id}",
                    target_id=f"classifier:{relation.target_id}",
                    relationship_kind=self.relationship_kind(relation.kind),
                    source_cardinality=ArchitectureCardinality(relation.source_cardinality.value),
                    target_cardinality=ArchitectureCardinality(relation.target_cardinality.value),
                )
            )
        identities = tuple(assertion.id for assertion in assertions)
        if len(identities) != len(set(identities)):
            raise ProjectsError(f"UML diagram {diagram.diagram_id!r} declares duplicate architecture assertions.")
        return tuple(sorted(assertions, key=lambda assertion: (assertion.kind.value, assertion.id)))
