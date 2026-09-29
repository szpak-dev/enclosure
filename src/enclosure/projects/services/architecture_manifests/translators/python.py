import ast
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Never, cast

from modwire.application import CapabilityStatus, FactCapability, ImplementationManifest
from wireup import injectable

from ....errors import ProjectsError
from ..assertions.model import (
    ArchitectureArtifactKind,
    ArchitectureAssertionKind,
    ArchitectureCardinality,
    ArchitectureClassifierKind,
    ArchitectureMemberKind,
    ArchitectureMemberOwnership,
    ArchitectureParameter,
    ArchitectureRelationshipKind,
    ArchitectureTypeReference,
    ArchitectureVisibility,
)
from ..evidence.model import (
    ArchitectureSupportState,
    ArtifactEvidence,
    ClassifierEvidence,
    EvidenceCapability,
    EvidenceProviderReceipt,
    ImplementationEvidence,
    ImplementationEvidenceSet,
    ImplementationLocator,
    MemberEvidence,
    ProviderManifest,
    RelationshipEvidence,
)
from .base import ImplementationSemanticTranslator


@injectable(as_type=ImplementationSemanticTranslator, qualifier="modwire-python-semantics")
@dataclass(frozen=True)
class ModwirePythonSemanticTranslator(ImplementationSemanticTranslator, ast.NodeVisitor):
    provider: str = field(default="modwire", init=False)
    language: str = field(default="python", init=False)
    order: int = field(default=10, init=False)

    def type_reference(self, expression: str) -> ArchitectureTypeReference:
        if not expression:
            return ArchitectureTypeReference(
                name="Unknown",
                arguments=(),
                cardinality=ArchitectureCardinality.ONE,
            )
        try:
            node = ast.parse(expression, mode="eval").body
        except SyntaxError as error:
            raise ProjectsError(f"Python type expression {expression!r} is invalid.") from error
        return cast(ArchitectureTypeReference, self.visit(node))

    def visit_Name(self, node: ast.Name) -> ArchitectureTypeReference:
        return ArchitectureTypeReference(
            name=self.canonical_type_name(node.id),
            arguments=(),
            cardinality=ArchitectureCardinality.ONE,
        )

    def visit_Attribute(self, node: ast.Attribute) -> ArchitectureTypeReference:
        return ArchitectureTypeReference(
            name=self.canonical_type_name(ast.unparse(node)),
            arguments=(),
            cardinality=ArchitectureCardinality.ONE,
        )

    def visit_Constant(self, node: ast.Constant) -> ArchitectureTypeReference:
        return ArchitectureTypeReference(
            name=self.canonical_type_name(str(node.value)),
            arguments=(),
            cardinality=ArchitectureCardinality.ONE,
        )

    def visit_Tuple(self, node: ast.Tuple) -> ArchitectureTypeReference:
        return ArchitectureTypeReference(
            name="Arguments",
            arguments=tuple(cast(ArchitectureTypeReference, self.visit(item)) for item in node.elts),
            cardinality=ArchitectureCardinality.ONE,
        )

    def visit_BinOp(self, node: ast.BinOp) -> ArchitectureTypeReference:
        if type(node.op) is not ast.BitOr:
            raise ProjectsError(f"Python type operator {type(node.op).__name__!r} is unsupported.")
        members = (
            cast(ArchitectureTypeReference, self.visit(node.left)),
            cast(ArchitectureTypeReference, self.visit(node.right)),
        )
        concrete = tuple(member for member in members if member.name != "Void")
        if len(concrete) == 1:
            return concrete[0].model_copy(update={"cardinality": ArchitectureCardinality.OPTIONAL})
        return ArchitectureTypeReference(
            name="Choice",
            arguments=members,
            cardinality=ArchitectureCardinality.ONE,
        )

    def visit_Subscript(self, node: ast.Subscript) -> ArchitectureTypeReference:
        name = ast.unparse(node.value)
        translated = cast(ArchitectureTypeReference, self.visit(node.slice))
        arguments = translated.arguments if translated.name == "Arguments" else (translated,)
        leaf = name.rsplit(".", maxsplit=1)[-1].casefold()
        if leaf in {"optional", "maybe"} and len(arguments) == 1:
            return arguments[0].model_copy(update={"cardinality": ArchitectureCardinality.OPTIONAL})
        if leaf in {"list", "sequence", "set", "tuple", "collection", "iterable"} and arguments:
            return arguments[0].model_copy(update={"cardinality": ArchitectureCardinality.MANY})
        if leaf == "union":
            concrete = tuple(argument for argument in arguments if argument.name != "Void")
            if len(concrete) == 1 and len(concrete) != len(arguments):
                return concrete[0].model_copy(update={"cardinality": ArchitectureCardinality.OPTIONAL})
            return ArchitectureTypeReference(
                name="Choice",
                arguments=arguments,
                cardinality=ArchitectureCardinality.ONE,
            )
        return ArchitectureTypeReference(
            name=self.canonical_type_name(name),
            arguments=arguments,
            cardinality=ArchitectureCardinality.ONE,
        )

    def generic_visit(self, node: ast.AST) -> Never:
        raise ProjectsError(f"Python type expression {ast.unparse(node)!r} is unsupported.")

    def canonical_type_name(self, value: str) -> str:
        leaf = value.rsplit(".", maxsplit=1)[-1]
        return {
            "str": "String",
            "int": "Integer",
            "bool": "Boolean",
            "float": "Number",
            "bytes": "Binary",
            "None": "Void",
            "NoneType": "Void",
            "dict": "Map",
            "Mapping": "Map",
            "Any": "Unknown",
        }.get(leaf, leaf)

    def visibility(self, value: str) -> ArchitectureVisibility:
        try:
            return ArchitectureVisibility(value)
        except ValueError as error:
            raise ProjectsError(f"Python visibility {value!r} has no canonical architecture meaning.") from error

    def support(
        self,
        manifest: ImplementationManifest,
        kind: ArchitectureAssertionKind,
    ) -> EvidenceCapability:
        if kind in {ArchitectureAssertionKind.ENTITY, ArchitectureAssertionKind.ENTITY_FIELD}:
            return EvidenceCapability(
                kind=kind,
                support=ArchitectureSupportState.UNSUPPORTED,
                explanation="Assigned-value evidence is required before entity semantics can be translated.",
            )
        dependencies = {
            ArchitectureAssertionKind.ARTIFACT: (FactCapability.SOURCES,),
            ArchitectureAssertionKind.CLASSIFIER: (
                FactCapability.SYMBOLS,
                FactCapability.INHERITANCE,
            ),
            ArchitectureAssertionKind.MEMBER: (
                FactCapability.SYMBOLS,
                FactCapability.CALLABLES,
                FactCapability.PARAMETERS,
                FactCapability.ANNOTATIONS,
                FactCapability.MODIFIERS,
                FactCapability.ATTRIBUTES,
            ),
            ArchitectureAssertionKind.RELATIONSHIP: (
                FactCapability.SYMBOLS,
                FactCapability.INHERITANCE,
                FactCapability.DEPENDENCIES,
            ),
        }[kind]
        declarations = tuple(
            coverage for coverage in manifest.producer.capabilities if coverage.capability in dependencies
        )
        if len(declarations) != len(dependencies):
            raise ProjectsError(f"Modwire did not declare every capability required for {kind.value!r} evidence.")
        unsupported = tuple(
            coverage for coverage in declarations if coverage.status == CapabilityStatus.UNSUPPORTED
        )
        if unsupported:
            return EvidenceCapability(
                kind=kind,
                support=ArchitectureSupportState.UNSUPPORTED,
                explanation="; ".join(coverage.explanation for coverage in unsupported),
            )
        partial = tuple(coverage for coverage in declarations if coverage.status == CapabilityStatus.PARTIAL)
        if kind == ArchitectureAssertionKind.RELATIONSHIP:
            return EvidenceCapability(
                kind=kind,
                support=ArchitectureSupportState.PARTIAL,
                explanation="Only statically resolved inheritance and source dependencies are observable.",
            )
        if partial:
            return EvidenceCapability(
                kind=kind,
                support=ArchitectureSupportState.PARTIAL,
                explanation="; ".join(coverage.explanation for coverage in partial),
            )
        return EvidenceCapability(kind=kind, support=ArchitectureSupportState.SUPPORTED, explanation="")

    def translate(self, provider_manifest: ProviderManifest) -> ImplementationEvidenceSet:
        manifest = cast(ImplementationManifest, provider_manifest.payload)
        source_paths = {str(source.source_id): source.relative_path for source in manifest.source_manifest.sources}
        symbol_by_id = {symbol.id.canonical(): symbol for symbol in manifest.symbols}
        classifier_families = {"class", "abstract_class", "interface"}
        classifier_symbols = tuple(
            symbol for symbol in manifest.symbols if symbol.id.family.value in classifier_families
        )
        classifier_ids = {
            symbol.id.canonical(): f"modwire:classifier:{symbol.id.canonical()}" for symbol in classifier_symbols
        }
        enumeration_ids = {
            relation.source_symbol_id.canonical()
            for relation in manifest.inheritance
            if relation.target_reference.rsplit(".", maxsplit=1)[-1]
            in {"Enum", "Flag", "IntEnum", "IntFlag", "StrEnum"}
        }
        classifiers_by_location = {
            (source_paths[str(symbol.id.source_id)], symbol.qualified_name): classifier_ids[symbol.id.canonical()]
            for symbol in classifier_symbols
        }
        annotations_by_target = {
            target: tuple(
                annotation
                for annotation in manifest.annotations
                if annotation.target_id == target
            )
            for target in {annotation.target_id for annotation in manifest.annotations}
        }
        evidence: list[ImplementationEvidence] = []
        source_directories = {
            str(parent)
            for source in manifest.source_manifest.sources
            for parent in PurePosixPath(source.relative_path).parents
            if str(parent) != "."
        }
        evidence.extend(
            ArtifactEvidence(
                id=f"modwire:artifact:directory:{path}",
                kind=ArchitectureAssertionKind.ARTIFACT,
                locator=ImplementationLocator(provider=self.provider, coordinate=path, path=path),
                reference=path,
                path=path,
                artifact_kind=ArchitectureArtifactKind.DIRECTORY,
                content_digest="",
            )
            for path in sorted(source_directories)
        )
        evidence.extend(
            ArtifactEvidence(
                id=f"modwire:artifact:file:{source.relative_path}",
                kind=ArchitectureAssertionKind.ARTIFACT,
                locator=ImplementationLocator(
                    provider=self.provider,
                    coordinate=str(source.source_id),
                    path=source.relative_path,
                ),
                reference=source.relative_path,
                path=source.relative_path,
                artifact_kind=ArchitectureArtifactKind.FILE,
                content_digest=source.content_digest,
            )
            for source in manifest.source_manifest.sources
        )
        evidence.extend(
            ClassifierEvidence(
                id=classifier_ids[symbol.id.canonical()],
                kind=ArchitectureAssertionKind.CLASSIFIER,
                locator=ImplementationLocator(
                    provider=self.provider,
                    coordinate=symbol.id.canonical(),
                    path=source_paths[str(symbol.id.source_id)],
                ),
                reference=symbol.qualified_name.rsplit(".", maxsplit=1)[-1],
                name=symbol.qualified_name.rsplit(".", maxsplit=1)[-1],
                classifier_kind=(
                    ArchitectureClassifierKind.INTERFACE
                    if symbol.id.family.value == "interface"
                    else ArchitectureClassifierKind.ENUMERATION
                    if symbol.id.canonical() in enumeration_ids
                    else ArchitectureClassifierKind.CLASS
                ),
                abstract=symbol.id.family.value in {"abstract_class", "interface"},
            )
            for symbol in classifier_symbols
        )
        parameter_annotations = {
            parameter.id: tuple(
                annotation.expression
                for annotation in annotations_by_target.get(parameter.id, ())
                if annotation.role == "parameter_type"
            )
            for parameter in manifest.parameters
        }
        parameters_by_callable = {
            callable_id: tuple(
                sorted(
                    (
                        ArchitectureParameter(
                            name=parameter.name,
                            position=parameter.position,
                            type=self.type_reference(
                                parameter_annotations[parameter.id][0]
                                if parameter_annotations[parameter.id]
                                else "Unknown"
                            ),
                        )
                        for parameter in manifest.parameters
                        if parameter.callable_id.canonical() == callable_id
                    ),
                    key=lambda parameter: (parameter.position, parameter.name),
                )
            )
            for callable_id in {item.symbol_id.canonical() for item in manifest.callables}
        }
        for attribute in manifest.attributes:
            if attribute.owner_symbol_id.canonical() not in classifier_ids:
                continue
            owner_id = classifier_ids[attribute.owner_symbol_id.canonical()]
            type_reference = self.type_reference(attribute.annotation)
            if attribute.is_optional:
                type_reference = type_reference.model_copy(update={"cardinality": ArchitectureCardinality.OPTIONAL})
            evidence.append(
                MemberEvidence(
                    id=f"modwire:member:attribute:{attribute.id}",
                    kind=ArchitectureAssertionKind.MEMBER,
                    locator=ImplementationLocator(
                        provider=self.provider,
                        coordinate=attribute.id,
                        path=source_paths[str(attribute.owner_symbol_id.source_id)],
                    ),
                    reference=attribute.name,
                    owner_id=owner_id,
                    name=attribute.name,
                    member_kind=ArchitectureMemberKind.PROPERTY,
                    type=type_reference,
                    visibility=self.visibility(attribute.visibility),
                    ownership=(
                        ArchitectureMemberOwnership.TYPE
                        if attribute.member_kind.value == "static"
                        else ArchitectureMemberOwnership.INSTANCE
                    ),
                    abstract=False,
                    parameters=(),
                )
            )
        for callable_value in manifest.callables:
            symbol = symbol_by_id[callable_value.symbol_id.canonical()]
            owner_name, separator, operation_name = symbol.qualified_name.rpartition(".")
            owner_location = (source_paths[str(symbol.id.source_id)], owner_name)
            if not separator or owner_location not in classifiers_by_location:
                continue
            owner_id = classifiers_by_location[owner_location]
            annotations = annotations_by_target.get(symbol.id.canonical(), ())
            return_types = tuple(
                annotation.expression for annotation in annotations if annotation.role == "return_type"
            )
            decorators = {
                annotation.expression.rsplit(".", maxsplit=1)[-1]
                for annotation in annotations
                if annotation.role == "decorator"
            }
            operation_type = (
                ArchitectureTypeReference(
                    name="Void",
                    arguments=(),
                    cardinality=ArchitectureCardinality.ONE,
                )
                if operation_name == "__init__"
                else self.type_reference(return_types[0] if return_types else "Unknown")
            )
            evidence.append(
                MemberEvidence(
                    id=f"modwire:member:callable:{callable_value.symbol_id.canonical()}",
                    kind=ArchitectureAssertionKind.MEMBER,
                    locator=ImplementationLocator(
                        provider=self.provider,
                        coordinate=callable_value.symbol_id.canonical(),
                        path=source_paths[str(symbol.id.source_id)],
                    ),
                    reference="construct" if operation_name == "__init__" else operation_name,
                    owner_id=owner_id,
                    name="construct" if operation_name == "__init__" else operation_name,
                    member_kind=ArchitectureMemberKind.OPERATION,
                    type=operation_type,
                    visibility=self.visibility(symbol.visibility),
                    ownership=(
                        ArchitectureMemberOwnership.TYPE
                        if callable_value.callable_kind in {"static_method", "type_method"}
                        else ArchitectureMemberOwnership.INSTANCE
                    ),
                    abstract="abstractmethod" in decorators,
                    parameters=parameters_by_callable[callable_value.symbol_id.canonical()],
                )
            )
        for relation in manifest.inheritance:
            if relation.source_symbol_id.canonical() not in classifier_ids:
                continue
            source_id = classifier_ids[relation.source_symbol_id.canonical()]
            coordinate = (
                f"{relation.source_symbol_id.canonical()}:{relation.kind.value}:{relation.target_reference}"
            )
            evidence.append(
                RelationshipEvidence(
                    id=f"modwire:relationship:inheritance:{coordinate}",
                    kind=ArchitectureAssertionKind.RELATIONSHIP,
                    locator=ImplementationLocator(
                        provider=self.provider,
                        coordinate=coordinate,
                        path=source_paths[str(relation.source_symbol_id.source_id)],
                    ),
                    reference=relation.target_reference.rsplit(".", maxsplit=1)[-1],
                    source_id=source_id,
                    target_reference=relation.target_reference.rsplit(".", maxsplit=1)[-1],
                    relationship_kind=(
                        ArchitectureRelationshipKind.REALIZATION
                        if relation.kind.value == "implements"
                        else ArchitectureRelationshipKind.GENERALIZATION
                    ),
                    source_cardinality=ArchitectureCardinality.ONE,
                    target_cardinality=ArchitectureCardinality.ONE,
                )
            )
        classifiers_by_path: dict[str, list[ClassifierEvidence]] = {}
        for item in evidence:
            if item.kind == ArchitectureAssertionKind.CLASSIFIER:
                classifier = cast(ClassifierEvidence, item)
                classifiers_by_path.setdefault(classifier.locator.path, []).append(classifier)
        for dependency in manifest.dependencies:
            if dependency.target_kind != "source" or dependency.resolution != "resolved":
                continue
            source_path = source_paths[dependency.source_id]
            target_path = source_paths[dependency.target]
            for source in classifiers_by_path.get(source_path, []):
                for target in classifiers_by_path.get(target_path, []):
                    coordinate = (
                        f"{dependency.source_id}:{dependency.kind.value}:{dependency.target}:"
                        f"{dependency.specifier}:{source.id}:{target.id}"
                    )
                    evidence.append(
                        RelationshipEvidence(
                            id=f"modwire:relationship:dependency:{coordinate}",
                            kind=ArchitectureAssertionKind.RELATIONSHIP,
                            locator=ImplementationLocator(
                                provider=self.provider,
                                coordinate=coordinate,
                                path=source_path,
                            ),
                            reference=target.name,
                            source_id=source.id,
                            target_reference=target.name,
                            relationship_kind=ArchitectureRelationshipKind.DEPENDENCY,
                            source_cardinality=ArchitectureCardinality.ONE,
                            target_cardinality=ArchitectureCardinality.ONE,
                        )
                    )
        capabilities = tuple(self.support(manifest, kind) for kind in ArchitectureAssertionKind)
        return ImplementationEvidenceSet(
            receipt=EvidenceProviderReceipt(
                provider=provider_manifest.provider,
                version=provider_manifest.version,
                language=provider_manifest.language,
                source_digest=provider_manifest.source_digest,
                capabilities=capabilities,
            ),
            evidence=tuple(sorted(evidence, key=lambda item: (item.kind.value, item.id))),
        )
