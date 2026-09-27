from dataclasses import dataclass, field

from wireup import injectable

from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics

from ....errors import ProjectsError
from ...architecture_contracts.model import (
    ArchitectureContractDiagram,
    ArchitectureContractUnit,
    ArchitectureDiagramRole,
)
from ..facts.model import (
    AnnotationContractFact,
    ArchitectureContractFact,
    ArchitectureDiagramEvidence,
    ArchitectureFactCapability,
    AttributeContractFact,
    CallableContractFact,
    DependencyContractFact,
    InheritanceContractFact,
    ModifierContractFact,
    ParameterContractFact,
    SymbolContractFact,
)
from .base import ArchitectureDiagramCompiler


@injectable(as_type=ArchitectureDiagramCompiler, qualifier="uml-manifest")
@dataclass(frozen=True)
class UmlArchitectureCompiler(ArchitectureDiagramCompiler):
    role: ArchitectureDiagramRole = field(default=ArchitectureDiagramRole.UML, init=False)
    order: int = field(default=20, init=False)

    def compile(
        self,
        unit: ArchitectureContractUnit,
        diagram: ArchitectureContractDiagram,
        semantics: DiagramContractSemantics,
    ) -> tuple[ArchitectureContractFact, ...]:
        facts: list[ArchitectureContractFact] = []
        symbols = {symbol.element_id: symbol for symbol in semantics.symbols}
        identities: dict[str, tuple[str, str, str]] = {}
        for symbol in semantics.symbols:
            path, separator, declaration = symbol.element_id.partition("::")
            family, family_separator, qualified_name = declaration.partition(":")
            if not separator or not family_separator or not path or not family or not qualified_name:
                raise ProjectsError(
                    f"UML symbol identity {symbol.element_id!r} must be "
                    "'<project-relative-path>::<family>:<qualified-name>'."
                )
            identities[symbol.element_id] = (path, family, qualified_name)
        for symbol in semantics.symbols:
            path, family, qualified_name = identities[symbol.element_id]
            if unit.source_root != "." and path != unit.source_root and not path.startswith(f"{unit.source_root}/"):
                raise ProjectsError(
                    f"UML symbol {symbol.element_id!r} is outside contract source root {unit.source_root!r}."
                )
            symbol_fact_id = f"symbol:{symbol.element_id}"
            evidence = (
                ArchitectureDiagramEvidence(
                    diagram_id=diagram.diagram_id,
                    diagram_revision=diagram.diagram_revision,
                    element_id=symbol.element_id,
                ),
            )
            facts.append(
                SymbolContractFact(
                    id=symbol_fact_id,
                    capability=ArchitectureFactCapability.SYMBOLS,
                    required=True,
                    evidence=evidence,
                    path=path,
                    family=family,
                    qualified_name=qualified_name,
                    kind=family,
                )
            )
            facts.extend(
                AnnotationContractFact(
                    id=f"annotation:{symbol_fact_id}:decorator:{annotation}",
                    capability=ArchitectureFactCapability.ANNOTATIONS,
                    required=True,
                    evidence=evidence,
                    target_id=symbol_fact_id,
                    role="decorator",
                    expression=annotation,
                )
                for annotation in symbol.annotations
            )
            for member in symbol.members:
                if member.kind == "attribute":
                    attribute_fact_id = f"attribute:{symbol_fact_id}:{member.name}"
                    facts.append(
                        AttributeContractFact(
                            id=attribute_fact_id,
                            capability=ArchitectureFactCapability.ATTRIBUTES,
                            required=True,
                            evidence=evidence,
                            owner_id=symbol_fact_id,
                            name=member.name,
                            optional=member.type.startswith("Optional[") or member.type.endswith("?"),
                        )
                    )
                    facts.append(
                        AnnotationContractFact(
                            id=f"annotation:{attribute_fact_id}:attribute_type:{member.type}",
                            capability=ArchitectureFactCapability.ANNOTATIONS,
                            required=True,
                            evidence=evidence,
                            target_id=attribute_fact_id,
                            role="attribute_type",
                            expression=member.type,
                        )
                    )
                    facts.extend(
                        (
                            ModifierContractFact(
                                id=f"modifier:{attribute_fact_id}:visibility:{member.visibility}",
                                capability=ArchitectureFactCapability.MODIFIERS,
                                required=True,
                                evidence=evidence,
                                target_id=attribute_fact_id,
                                role="visibility",
                                value=member.visibility,
                            ),
                            ModifierContractFact(
                                id=f"modifier:{attribute_fact_id}:member_kind:{member.modifier}",
                                capability=ArchitectureFactCapability.MODIFIERS,
                                required=True,
                                evidence=evidence,
                                target_id=attribute_fact_id,
                                role="member_kind",
                                value=member.modifier,
                            ),
                        )
                    )
                if member.kind == "method":
                    method_identity = f"{path}::method:{qualified_name}.{member.name}"
                    method_symbol_id = f"symbol:{method_identity}"
                    if member.name == "__init__":
                        callable_kind = "constructor"
                    elif member.modifier == "static":
                        callable_kind = "static_method"
                    else:
                        callable_kind = "instance_method"
                    facts.append(
                        SymbolContractFact(
                            id=method_symbol_id,
                            capability=ArchitectureFactCapability.SYMBOLS,
                            required=True,
                            evidence=evidence,
                            path=path,
                            family="method",
                            qualified_name=f"{qualified_name}.{member.name}",
                            kind="callable",
                        )
                    )
                    facts.append(
                        CallableContractFact(
                            id=f"callable:{method_symbol_id}",
                            capability=ArchitectureFactCapability.CALLABLES,
                            required=True,
                            evidence=evidence,
                            owner_id=method_symbol_id,
                            callable_kind=callable_kind,
                        )
                    )
                    facts.append(
                        AnnotationContractFact(
                            id=f"annotation:{method_symbol_id}:return_type:{member.type}",
                            capability=ArchitectureFactCapability.ANNOTATIONS,
                            required=True,
                            evidence=evidence,
                            target_id=method_symbol_id,
                            role="return_type",
                            expression=member.type,
                        )
                    )
                    if member.modifier == "abstract":
                        facts.append(
                            AnnotationContractFact(
                                id=f"annotation:{method_symbol_id}:decorator:abstractmethod",
                                capability=ArchitectureFactCapability.ANNOTATIONS,
                                required=True,
                                evidence=evidence,
                                target_id=method_symbol_id,
                                role="decorator",
                                expression="abstractmethod",
                            )
                        )
                    facts.extend(
                        ParameterContractFact(
                            id=f"parameter:{method_symbol_id}:{parameter.position}:{parameter.name}",
                            capability=ArchitectureFactCapability.PARAMETERS,
                            required=True,
                            evidence=evidence,
                            owner_id=method_symbol_id,
                            position=parameter.position,
                            name=parameter.name,
                            annotation=parameter.type,
                        )
                        for parameter in member.parameters
                    )
        for relation in semantics.relations:
            if relation.source_id not in symbols or relation.target_id not in symbols:
                raise ProjectsError(f"UML relation {relation.id!r} references an undeclared symbol identity.")
            source_path, _, _ = identities[relation.source_id]
            target_path, _, _ = identities[relation.target_id]
            source_fact_id = f"symbol:{relation.source_id}"
            evidence = (
                ArchitectureDiagramEvidence(
                    diagram_id=diagram.diagram_id,
                    diagram_revision=diagram.diagram_revision,
                    element_id=relation.id,
                ),
            )
            if relation.kind == "inheritance":
                facts.append(
                    InheritanceContractFact(
                        id=f"inheritance:{source_fact_id}:{relation.kind}:{symbols[relation.target_id].label}",
                        capability=ArchitectureFactCapability.INHERITANCE,
                        required=True,
                        evidence=evidence,
                        owner_id=source_fact_id,
                        kind=relation.kind,
                        target=symbols[relation.target_id].label,
                    )
                )
            if relation.kind == "dependency":
                if not relation.label:
                    raise ProjectsError(
                        f"UML dependency {relation.id!r} must label the exact implementation specifier."
                    )
                facts.append(
                    DependencyContractFact(
                        id=(f"dependency:{source_path}:{target_path}:{relation.kind}:{relation.label}"),
                        capability=ArchitectureFactCapability.DEPENDENCIES,
                        required=True,
                        evidence=evidence,
                        source_path=source_path,
                        kind=relation.kind,
                        target=target_path,
                        specifier=relation.label,
                        resolution="resolved",
                    )
                )
        fact_identities = tuple(fact.id for fact in facts)
        if len(fact_identities) != len(set(fact_identities)):
            raise ProjectsError(f"UML diagram {diagram.diagram_id!r} declares duplicate architecture facts.")
        return tuple(sorted(facts, key=lambda fact: (fact.capability.value, fact.id)))
