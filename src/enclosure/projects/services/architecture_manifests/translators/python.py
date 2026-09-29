import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Never, cast

from modwire.application import (
    CapabilityStatus,
    FactCapability,
    ImplementationManifest,
    SourceAssignedValue,
    SourceAssignedValueKind,
)
from wireup import injectable

from ....errors import ProjectsError
from ..assertions.model import (
    ArchitectureArtifactKind,
    ArchitectureAssertionKind,
    ArchitectureCardinality,
    ArchitectureClassifierKind,
    ArchitectureEntityKey,
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
    EntityEvidence,
    EntityFieldEvidence,
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
    field_types: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(
            {
                "AutoField": "int",
                "BigAutoField": "int",
                "BigIntegerField": "int",
                "BinaryField": "binary",
                "BooleanField": "boolean",
                "CharField": "string",
                "DateField": "date",
                "DateTimeField": "datetime",
                "DecimalField": "decimal",
                "DurationField": "duration",
                "EmailField": "string",
                "FileField": "string",
                "FloatField": "float",
                "IntegerField": "int",
                "JSONField": "json",
                "PositiveBigIntegerField": "int",
                "PositiveIntegerField": "int",
                "PositiveSmallIntegerField": "int",
                "SlugField": "string",
                "SmallAutoField": "int",
                "SmallIntegerField": "int",
                "ShortUUIDField": "string",
                "TextField": "string",
                "TimeField": "time",
                "URLField": "string",
                "UUIDField": "string",
            }
        ),
        init=False,
        repr=False,
    )

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

    def assigned_call(self, value: SourceAssignedValue) -> ast.Call:
        try:
            return cast(ast.Call, ast.parse(value.expression, mode="eval").body)
        except SyntaxError as error:
            raise ProjectsError(f"Python assigned call {value.expression!r} is invalid.") from error

    def call_keyword(self, call: ast.Call, name: str) -> str:
        values = tuple(ast.unparse(keyword.value) for keyword in call.keywords if keyword.arg == name)
        if len(values) > 1:
            raise ProjectsError(f"Python call declares keyword {name!r} more than once.")
        return values[0] if values else ""

    def entity_field_name(self, name: str, field_reference: str) -> str:
        if field_reference in {"ForeignKey", "OneToOneField"}:
            return f"{name}_id"
        return name

    def entity_name(self, value: str) -> str:
        name = value.rsplit(".", maxsplit=1)[-1]
        return name.removesuffix("Model") or name

    def entity_field_type(
        self,
        field_reference: str,
        call: ast.Call,
        cardinality: ArchitectureCardinality,
    ) -> ArchitectureTypeReference:
        choices = self.call_keyword(call, "choices")
        if choices:
            name = choices.removesuffix(".choices").rsplit(".", maxsplit=1)[-1]
        elif field_reference in {"ForeignKey", "OneToOneField", "ManyToManyField"}:
            name = "string"
        else:
            name = self.field_types.get(field_reference, field_reference.removesuffix("Field").casefold())
        return ArchitectureTypeReference(name=name, arguments=(), cardinality=cardinality)

    def entity_field_keys(self, field_reference: str, call: ast.Call) -> tuple[ArchitectureEntityKey, ...]:
        primary = self.call_keyword(call, "primary_key") == "True"
        unique = self.call_keyword(call, "unique") == "True" or field_reference == "OneToOneField"
        foreign = field_reference in {"ForeignKey", "OneToOneField", "ManyToManyField"}
        return tuple(
            key
            for key, present in (
                (ArchitectureEntityKey.FOREIGN, foreign),
                (ArchitectureEntityKey.PRIMARY, primary),
                (ArchitectureEntityKey.UNIQUE, unique),
            )
            if present
        )

    def entity_field_cardinality(self, field_reference: str, call: ast.Call) -> ArchitectureCardinality:
        if field_reference == "ManyToManyField":
            return ArchitectureCardinality.MANY
        if self.call_keyword(call, "null") == "True":
            return ArchitectureCardinality.OPTIONAL
        return ArchitectureCardinality.ONE

    def relationship_target(self, call: ast.Call) -> str:
        if not call.args:
            return ""
        return self.entity_name(ast.unparse(call.args[0]).strip("'\""))

    def support(
        self,
        manifest: ImplementationManifest,
        kind: ArchitectureAssertionKind,
    ) -> EvidenceCapability:
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
            ArchitectureAssertionKind.ENTITY: (
                FactCapability.SYMBOLS,
                FactCapability.ATTRIBUTES,
                FactCapability.ASSIGNED_VALUES,
                FactCapability.INHERITANCE,
            ),
            ArchitectureAssertionKind.ENTITY_FIELD: (
                FactCapability.SYMBOLS,
                FactCapability.ATTRIBUTES,
                FactCapability.ASSIGNED_VALUES,
                FactCapability.INHERITANCE,
            ),
        }[kind]
        declarations = tuple(
            coverage for coverage in manifest.producer.capabilities if coverage.capability in dependencies
        )
        if len(declarations) != len(dependencies):
            raise ProjectsError(f"Modwire did not declare every capability required for {kind.value!r} evidence.")
        unsupported = tuple(coverage for coverage in declarations if coverage.status == CapabilityStatus.UNSUPPORTED)
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
                explanation=(
                    "Only statically resolved inheritance, source dependencies, and assigned relationship "
                    "fields are observable."
                ),
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
        classifiers_by_name = {
            name: tuple(
                symbol for symbol in classifier_symbols if symbol.qualified_name.rsplit(".", maxsplit=1)[-1] == name
            )
            for name in {symbol.qualified_name.rsplit(".", maxsplit=1)[-1] for symbol in classifier_symbols}
        }
        bases_by_classifier = {
            symbol.id.canonical(): tuple(
                relation.target_reference.rsplit(".", maxsplit=1)[-1]
                for relation in manifest.inheritance
                if relation.source_symbol_id.canonical() == symbol.id.canonical()
            )
            for symbol in classifier_symbols
        }
        model_classifier_ids = {
            symbol.id.canonical()
            for symbol in classifier_symbols
            if "Model" in bases_by_classifier[symbol.id.canonical()]
        }
        unresolved_model_ids = {
            symbol.id.canonical() for symbol in classifier_symbols if symbol.id.canonical() not in model_classifier_ids
        }
        while unresolved_model_ids:
            discovered = {
                symbol_id
                for symbol_id in unresolved_model_ids
                if any(
                    base in classifiers_by_name
                    and len(classifiers_by_name[base]) == 1
                    and classifiers_by_name[base][0].id.canonical() in model_classifier_ids
                    for base in bases_by_classifier[symbol_id]
                )
            }
            if not discovered:
                break
            model_classifier_ids.update(discovered)
            unresolved_model_ids.difference_update(discovered)
        abstract_model_names = {
            symbol.qualified_name.rsplit(".", maxsplit=1)[0]
            for symbol in classifier_symbols
            if symbol.qualified_name.endswith(".Meta")
            for attribute in manifest.attributes
            if attribute.owner_symbol_id.canonical() == symbol.id.canonical()
            and attribute.name == "abstract"
            and any(
                value.kind == SourceAssignedValueKind.LITERAL and value.expression == "True"
                for value in attribute.assigned_values
            )
        }
        entity_symbols = tuple(
            symbol
            for symbol in classifier_symbols
            if symbol.id.canonical() in model_classifier_ids and symbol.qualified_name not in abstract_model_names
        )
        entity_ids = {symbol.id.canonical(): f"modwire:entity:{symbol.id.canonical()}" for symbol in entity_symbols}
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
            target: tuple(annotation for annotation in manifest.annotations if annotation.target_id == target)
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
        evidence.extend(
            EntityEvidence(
                id=entity_ids[symbol.id.canonical()],
                kind=ArchitectureAssertionKind.ENTITY,
                locator=ImplementationLocator(
                    provider=self.provider,
                    coordinate=symbol.id.canonical(),
                    path=source_paths[str(symbol.id.source_id)],
                ),
                reference=self.entity_name(symbol.qualified_name),
                name=self.entity_name(symbol.qualified_name),
            )
            for symbol in entity_symbols
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
        attributes_by_owner = {
            symbol.id.canonical(): tuple(
                attribute
                for attribute in manifest.attributes
                if attribute.owner_symbol_id.canonical() == symbol.id.canonical()
            )
            for symbol in classifier_symbols
        }
        for entity_symbol in entity_symbols:
            inherited_names = list(bases_by_classifier[entity_symbol.id.canonical()])
            inherited_ids: list[str] = []
            while inherited_names:
                base_name = inherited_names.pop(0)
                if base_name not in classifiers_by_name or len(classifiers_by_name[base_name]) != 1:
                    continue
                base_id = classifiers_by_name[base_name][0].id.canonical()
                if base_id in inherited_ids:
                    continue
                inherited_ids.append(base_id)
                inherited_names.extend(bases_by_classifier[base_id])
            field_attributes = {
                attribute.name: attribute
                for owner_id in (*reversed(inherited_ids), entity_symbol.id.canonical())
                for attribute in attributes_by_owner[owner_id]
                if any(
                    value.kind == SourceAssignedValueKind.CALL
                    and value.reference.rsplit(".", maxsplit=1)[-1].endswith("Field")
                    for value in attribute.assigned_values
                )
            }
            for attribute in field_attributes.values():
                assigned_values = tuple(
                    value
                    for value in attribute.assigned_values
                    if value.kind == SourceAssignedValueKind.CALL
                    and value.reference.rsplit(".", maxsplit=1)[-1].endswith("Field")
                )
                if len(assigned_values) != 1:
                    raise ProjectsError(f"Entity field {attribute.id!r} has no unique assigned field call.")
                assigned_value = assigned_values[0]
                field_reference = assigned_value.reference.rsplit(".", maxsplit=1)[-1]
                call = self.assigned_call(assigned_value)
                cardinality = self.entity_field_cardinality(field_reference, call)
                evidence.append(
                    EntityFieldEvidence(
                        id=f"modwire:entity-field:{entity_symbol.id.canonical()}:{attribute.id}",
                        kind=ArchitectureAssertionKind.ENTITY_FIELD,
                        locator=ImplementationLocator(
                            provider=self.provider,
                            coordinate=attribute.id,
                            path=source_paths[str(attribute.owner_symbol_id.source_id)],
                        ),
                        reference=self.entity_field_name(attribute.name, field_reference),
                        owner_id=entity_ids[entity_symbol.id.canonical()],
                        name=self.entity_field_name(attribute.name, field_reference),
                        type=self.entity_field_type(field_reference, call, cardinality),
                        keys=self.entity_field_keys(field_reference, call),
                        cardinality=cardinality,
                    )
                )
                if field_reference not in {"ForeignKey", "OneToOneField", "ManyToManyField"}:
                    continue
                target_name = self.relationship_target(call)
                targets = tuple(
                    symbol for symbol in entity_symbols if self.entity_name(symbol.qualified_name) == target_name
                )
                if len(targets) != 1:
                    continue
                target = targets[0]
                keys = self.entity_field_keys(field_reference, call)
                evidence.append(
                    RelationshipEvidence(
                        id=f"modwire:relationship:entity:{entity_symbol.id.canonical()}:{attribute.id}",
                        kind=ArchitectureAssertionKind.RELATIONSHIP,
                        locator=ImplementationLocator(
                            provider=self.provider,
                            coordinate=attribute.id,
                            path=source_paths[str(attribute.owner_symbol_id.source_id)],
                        ),
                        reference=self.entity_name(entity_symbol.qualified_name),
                        source_id=entity_ids[target.id.canonical()],
                        target_reference=self.entity_name(entity_symbol.qualified_name),
                        relationship_kind=(
                            ArchitectureRelationshipKind.IDENTIFYING
                            if ArchitectureEntityKey.PRIMARY in keys
                            else ArchitectureRelationshipKind.NON_IDENTIFYING
                        ),
                        source_cardinality=(
                            ArchitectureCardinality.OPTIONAL
                            if self.call_keyword(call, "null") == "True"
                            else ArchitectureCardinality.ONE
                        ),
                        target_cardinality=(
                            ArchitectureCardinality.OPTIONAL
                            if field_reference == "OneToOneField"
                            else ArchitectureCardinality.MANY
                        ),
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
            coordinate = f"{relation.source_symbol_id.canonical()}:{relation.kind.value}:{relation.target_reference}"
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
