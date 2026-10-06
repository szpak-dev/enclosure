import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import groupby
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
    EvidenceSupport,
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
    scalar_types: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType(
            {
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
                "object": "Unknown",
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
        leaf = name.rsplit(".", maxsplit=1)[-1].casefold()
        if leaf == "annotated":
            if type(node.slice) is not ast.Tuple or len(node.slice.elts) < 2:
                raise ProjectsError("Python Annotated types require a base type and metadata.")
            return cast(ArchitectureTypeReference, self.visit(node.slice.elts[0]))
        if leaf == "serializeasany":
            if type(node.slice) is ast.Tuple:
                raise ProjectsError("Python SerializeAsAny types require exactly one base type.")
            return cast(ArchitectureTypeReference, self.visit(node.slice))
        if leaf == "callable":
            if type(node.slice) is not ast.Tuple or len(node.slice.elts) != 2:
                raise ProjectsError("Python Callable types require a parameter list and return type.")
            parameters, _returns = node.slice.elts
            if type(parameters) is not ast.List:
                raise ProjectsError("Python Callable parameters require an explicit type list.")
            return ArchitectureTypeReference(
                name=self.canonical_type_name(name),
                arguments=(),
                cardinality=ArchitectureCardinality.ONE,
            )
        translated = cast(ArchitectureTypeReference, self.visit(node.slice))
        arguments = translated.arguments if translated.name == "Arguments" else (translated,)
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
        return self.scalar_types.get(leaf, leaf)

    def attribute_type(
        self,
        annotation: str,
        assigned_values: tuple[SourceAssignedValue, ...],
        enumeration: bool,
    ) -> ArchitectureTypeReference:
        if annotation or not enumeration:
            return self.type_reference(annotation)
        literals = tuple(value for value in assigned_values if value.kind == SourceAssignedValueKind.LITERAL)
        if len(literals) != 1:
            return self.type_reference(annotation)
        try:
            value = ast.literal_eval(literals[0].expression)
        except (SyntaxError, ValueError):
            return self.type_reference(annotation)
        name = self.canonical_type_name(type(value).__name__)
        return ArchitectureTypeReference(name=name, arguments=(), cardinality=ArchitectureCardinality.ONE)

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

    def minimum_length(self, assigned_values: tuple[SourceAssignedValue, ...]) -> int | None:
        lengths: list[int] = []
        for value in assigned_values:
            if value.kind != SourceAssignedValueKind.CALL or value.reference.rsplit(".", maxsplit=1)[-1] != "Field":
                continue
            expression = self.call_keyword(self.assigned_call(value), "min_length")
            if not expression:
                continue
            try:
                length = ast.literal_eval(expression)
            except (SyntaxError, ValueError):
                continue
            if type(length) is int:
                lengths.append(length)
        return max(lengths) if lengths else None

    def public_http_response(self, decorators: tuple[str, ...]) -> str:
        responses: list[str] = []
        for expression in decorators:
            try:
                node = ast.parse(expression, mode="eval").body
            except SyntaxError as error:
                raise ProjectsError(f"Python decorator expression {expression!r} is invalid.") from error
            if type(node) is not ast.Call:
                continue
            values = tuple(keyword.value for keyword in node.keywords if keyword.arg == "response")
            if len(values) > 1:
                raise ProjectsError(f"Python decorator {expression!r} declares response more than once.")
            if len(values) == 1 and type(values[0]) in {ast.Name, ast.Attribute}:
                responses.append(ast.unparse(values[0]))
        if len(responses) > 1:
            raise ProjectsError("Python callable declares more than one public HTTP response type.")
        return responses[0] if responses else ""

    def is_entity_field_reference(self, value: SourceAssignedValue) -> bool:
        reference = value.reference.rsplit(".", maxsplit=1)[-1]
        return reference.endswith("Field") or reference == "ForeignKey"

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

    def entity_field_keys(
        self,
        field_reference: str,
        call: ast.Call,
        constrained_unique: bool = False,
    ) -> tuple[ArchitectureEntityKey, ...]:
        primary = self.call_keyword(call, "primary_key") == "True"
        foreign = field_reference in {"ForeignKey", "OneToOneField", "ManyToManyField"}
        unique = (
            self.call_keyword(call, "unique") == "True"
            or field_reference == "OneToOneField"
            or (constrained_unique and not foreign)
        )
        return tuple(
            key
            for key, present in (
                (ArchitectureEntityKey.FOREIGN, foreign),
                (ArchitectureEntityKey.PRIMARY, primary),
                (ArchitectureEntityKey.UNIQUE, unique),
            )
            if present
        )

    def unique_constraint_fields(self, expression: str) -> set[str]:
        try:
            root = ast.parse(expression, mode="eval").body
        except SyntaxError as error:
            raise ProjectsError(f"Python constraint expression {expression!r} is invalid.") from error
        fields: set[str] = set()
        for node in ast.walk(root):
            if type(node) is not ast.Call or ast.unparse(node.func).rsplit(".", maxsplit=1)[-1] != "UniqueConstraint":
                continue
            values = tuple(keyword.value for keyword in node.keywords if keyword.arg == "fields")
            if len(values) != 1 or type(values[0]) not in {ast.List, ast.Tuple}:
                continue
            for item in values[0].elts:
                if type(item) is ast.Constant and type(item.value) is str:
                    fields.add(item.value)
        return fields

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

    def referenced_type_names(self, value: ArchitectureTypeReference) -> tuple[str, ...]:
        containers = {"Arguments", "Callable", "Choice", "Collection", "Literal", "Map"}
        names = tuple(name for argument in value.arguments for name in self.referenced_type_names(argument))
        if value.name in containers or value.name in {
            "Binary",
            "Boolean",
            "Date",
            "Datetime",
            "Decimal",
            "Duration",
            "Integer",
            "Number",
            "String",
            "Time",
            "Unknown",
            "Void",
        }:
            return names
        return (value.name, *names)

    def support(
        self,
        manifest: ImplementationManifest,
        kind: ArchitectureAssertionKind,
    ) -> EvidenceCapability:
        semantic_dependencies = {
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
        inventory_dependencies = {
            ArchitectureAssertionKind.ARTIFACT: (FactCapability.SOURCES,),
            ArchitectureAssertionKind.CLASSIFIER: (FactCapability.SYMBOLS,),
            ArchitectureAssertionKind.MEMBER: (
                FactCapability.SYMBOLS,
                FactCapability.CALLABLES,
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
        return EvidenceCapability(
            kind=kind,
            semantics=self.capability_support(manifest, kind, semantic_dependencies),
            inventory=self.capability_support(manifest, kind, inventory_dependencies),
        )

    def capability_support(
        self,
        manifest: ImplementationManifest,
        kind: ArchitectureAssertionKind,
        dependencies: tuple[FactCapability, ...],
    ) -> EvidenceSupport:
        declarations = tuple(
            coverage for coverage in manifest.producer.capabilities if coverage.capability in dependencies
        )
        if len(declarations) != len(dependencies):
            raise ProjectsError(f"Modwire did not declare every capability required for {kind.value!r} evidence.")
        unsupported = tuple(coverage for coverage in declarations if coverage.status == CapabilityStatus.UNSUPPORTED)
        if unsupported:
            return EvidenceSupport(
                support=ArchitectureSupportState.UNSUPPORTED,
                explanation="; ".join(coverage.explanation for coverage in unsupported),
            )
        if kind == ArchitectureAssertionKind.RELATIONSHIP:
            return EvidenceSupport(
                support=ArchitectureSupportState.PARTIAL,
                explanation=(
                    "Only statically resolved inheritance, source dependencies, and assigned relationship "
                    "fields are observable."
                ),
            )
        partial = tuple(coverage for coverage in declarations if coverage.status == CapabilityStatus.PARTIAL)
        if partial:
            return EvidenceSupport(
                support=ArchitectureSupportState.PARTIAL,
                explanation="; ".join(coverage.explanation for coverage in partial),
            )
        return EvidenceSupport(support=ArchitectureSupportState.SUPPORTED, explanation="")

    def translate(self, provider_manifest: ProviderManifest) -> ImplementationEvidenceSet:
        manifest = cast(ImplementationManifest, provider_manifest.payload)
        source_paths = {str(source.source_id): source.relative_path for source in manifest.source_manifest.sources}
        source_paths_by_suffix: dict[str, list[str]] = {}
        for path in source_paths.values():
            parts = PurePosixPath(path).parts
            for position in range(len(parts)):
                source_paths_by_suffix.setdefault("/".join(parts[position:]), []).append(path)
        dependency_targets_by_path = {path: set() for path in source_paths.values()}
        for dependency in manifest.dependencies:
            source_path = source_paths[str(dependency.source_id)]
            if dependency.target_kind == "source" and dependency.resolution == "resolved":
                dependency_targets_by_path[source_path].add(source_paths[str(dependency.target)])
                continue
            if dependency.resolution != "unresolved" or dependency.specifier.startswith("."):
                continue
            module_suffix = f"{dependency.specifier.replace('.', '/')}.py"
            inferred = tuple(source_paths_by_suffix.get(module_suffix, ()))
            if len(inferred) == 1:
                dependency_targets_by_path[source_path].add(inferred[0])
        symbol_by_id = {symbol.id.canonical(): symbol for symbol in manifest.symbols}
        classifier_families = {"class", "abstract_class", "interface"}
        classifier_symbols = tuple(
            symbol for symbol in manifest.symbols if symbol.id.family.value in classifier_families
        )
        classifier_ids = {
            symbol.id.canonical(): f"modwire:classifier:{symbol.id.canonical()}" for symbol in classifier_symbols
        }
        classifier_references = {
            symbol.id.canonical(): (
                f"{source_paths[str(symbol.id.source_id)]}::{symbol.id.family.value}:{symbol.qualified_name}"
            )
            for symbol in classifier_symbols
        }
        classifiers_by_name = {
            name: tuple(values)
            for name, values in groupby(
                sorted(classifier_symbols, key=lambda item: item.qualified_name.rsplit(".", maxsplit=1)[-1]),
                key=lambda item: item.qualified_name.rsplit(".", maxsplit=1)[-1],
            )
        }
        classifiers_by_qualified_name = {
            name: tuple(values)
            for name, values in groupby(
                sorted(classifier_symbols, key=lambda item: item.qualified_name),
                key=lambda item: item.qualified_name,
            )
        }
        inheritance_by_source = {
            source: tuple(values)
            for source, values in groupby(
                sorted(manifest.inheritance, key=lambda item: item.source_symbol_id.canonical()),
                key=lambda item: item.source_symbol_id.canonical(),
            )
        }
        bases_by_classifier = {
            symbol.id.canonical(): tuple(
                relation.target_reference.rsplit(".", maxsplit=1)[-1]
                for relation in inheritance_by_source.get(symbol.id.canonical(), ())
            )
            for symbol in classifier_symbols
        }
        attributes_by_owner = {
            owner: tuple(values)
            for owner, values in groupby(
                sorted(manifest.attributes, key=lambda item: item.owner_symbol_id.canonical()),
                key=lambda item: item.owner_symbol_id.canonical(),
            )
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
        pydantic_classifier_ids = {
            symbol.id.canonical()
            for symbol in classifier_symbols
            if "BaseModel" in bases_by_classifier[symbol.id.canonical()]
        }
        unresolved_pydantic_ids = {
            symbol.id.canonical()
            for symbol in classifier_symbols
            if symbol.id.canonical() not in pydantic_classifier_ids
        }
        while unresolved_pydantic_ids:
            discovered = {
                symbol_id
                for symbol_id in unresolved_pydantic_ids
                if any(
                    base in classifiers_by_name
                    and len(classifiers_by_name[base]) == 1
                    and classifiers_by_name[base][0].id.canonical() in pydantic_classifier_ids
                    for base in bases_by_classifier[symbol_id]
                )
            }
            if not discovered:
                break
            pydantic_classifier_ids.update(discovered)
            unresolved_pydantic_ids.difference_update(discovered)
        nonempty_relationship_contracts: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for attribute in manifest.attributes:
            owner_symbol_id = attribute.owner_symbol_id.canonical()
            if owner_symbol_id not in pydantic_classifier_ids:
                continue
            minimum_length = self.minimum_length(attribute.assigned_values)
            type_reference = self.type_reference(attribute.annotation)
            if (
                minimum_length is None
                or minimum_length < 1
                or type_reference.cardinality != ArchitectureCardinality.MANY
            ):
                continue
            source_name = symbol_by_id[owner_symbol_id].qualified_name.rsplit(".", maxsplit=1)[-1]
            for target_name in self.referenced_type_names(type_reference):
                nonempty_relationship_contracts.setdefault((source_name, target_name), []).append(
                    (attribute.id, str(attribute.owner_symbol_id.source_id))
                )
        abstract_model_names = {
            symbol.qualified_name.rsplit(".", maxsplit=1)[0]
            for symbol in classifier_symbols
            if symbol.qualified_name.endswith(".Meta")
            for attribute in attributes_by_owner.get(symbol.id.canonical(), ())
            if attribute.name == "abstract"
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
            target: tuple(values)
            for target, values in groupby(
                sorted(manifest.annotations, key=lambda item: item.target_id),
                key=lambda item: item.target_id,
            )
        }
        public_http_responses = {
            callable_value.symbol_id.canonical(): response
            for callable_value in manifest.callables
            if (
                response := self.public_http_response(
                    tuple(
                        annotation.expression
                        for annotation in annotations_by_target.get(callable_value.symbol_id.canonical(), ())
                        if annotation.role == "decorator"
                    )
                )
            )
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
                reference=classifier_references[symbol.id.canonical()],
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
        parameter_values_by_callable = {
            callable_id: tuple(values)
            for callable_id, values in groupby(
                sorted(
                    manifest.parameters,
                    key=lambda item: (item.callable_id.canonical(), item.position, item.name),
                ),
                key=lambda item: item.callable_id.canonical(),
            )
        }
        parameters_by_callable = {}
        for callable_id in {item.symbol_id.canonical() for item in manifest.callables}:
            parameters = parameter_values_by_callable.get(callable_id, ())
            if (
                callable_id in public_http_responses
                and parameters
                and parameters[0].name == "request"
                and not parameter_annotations[parameters[0].id]
            ):
                parameters = parameters[1:]
            parameters_by_callable[callable_id] = tuple(
                ArchitectureParameter(
                    name=parameter.name,
                    position=position,
                    type=self.type_reference(
                        parameter_annotations[parameter.id][0] if parameter_annotations[parameter.id] else "Unknown"
                    ),
                )
                for position, parameter in enumerate(parameters)
            )
        for attribute in manifest.attributes:
            if attribute.owner_symbol_id.canonical() not in classifier_ids:
                continue
            owner_id = classifier_ids[attribute.owner_symbol_id.canonical()]
            type_reference = self.attribute_type(
                attribute.annotation,
                attribute.assigned_values,
                attribute.owner_symbol_id.canonical() in enumeration_ids,
            )
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
        meta_by_classifier: dict[str, str] = {}
        for source_id in {str(symbol.id.source_id) for symbol in classifier_symbols}:
            owner_id = ""
            for symbol in sorted(
                (item for item in classifier_symbols if str(item.id.source_id) == source_id),
                key=lambda item: item.id.ordinal,
            ):
                if symbol.qualified_name.rsplit(".", maxsplit=1)[-1] == "Meta":
                    if owner_id:
                        meta_by_classifier[owner_id] = symbol.id.canonical()
                    continue
                owner_id = symbol.id.canonical()
        unique_fields_by_classifier = {
            classifier_id: {
                field_name
                for attribute in attributes_by_owner.get(meta_id, ())
                if attribute.name == "constraints"
                for assigned_value in attribute.assigned_values
                if assigned_value.kind == SourceAssignedValueKind.LITERAL
                for field_name in self.unique_constraint_fields(assigned_value.expression)
            }
            for classifier_id, meta_id in meta_by_classifier.items()
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
                for attribute in attributes_by_owner.get(owner_id, ())
                if any(
                    value.kind == SourceAssignedValueKind.CALL and self.is_entity_field_reference(value)
                    for value in attribute.assigned_values
                )
            }
            for attribute in field_attributes.values():
                assigned_values = tuple(
                    value
                    for value in attribute.assigned_values
                    if value.kind == SourceAssignedValueKind.CALL and self.is_entity_field_reference(value)
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
                        keys=self.entity_field_keys(
                            field_reference,
                            call,
                            attribute.name in unique_fields_by_classifier.get(entity_symbol.id.canonical(), set()),
                        ),
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
                keys = self.entity_field_keys(
                    field_reference,
                    call,
                    attribute.name in unique_fields_by_classifier.get(entity_symbol.id.canonical(), set()),
                )
                constrained_unique = attribute.name in unique_fields_by_classifier.get(
                    entity_symbol.id.canonical(), set()
                )
                relationship_kind = (
                    ArchitectureRelationshipKind.IDENTIFYING
                    if ArchitectureEntityKey.PRIMARY in keys or constrained_unique
                    else ArchitectureRelationshipKind.NON_IDENTIFYING
                )
                source_cardinality = (
                    ArchitectureCardinality.OPTIONAL
                    if self.call_keyword(call, "null") == "True"
                    else ArchitectureCardinality.ONE
                )
                source_name = self.entity_name(target.qualified_name)
                target_name = self.entity_name(entity_symbol.qualified_name)
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
                        relationship_kind=relationship_kind,
                        source_cardinality=source_cardinality,
                        target_cardinality=(
                            ArchitectureCardinality.OPTIONAL
                            if field_reference == "OneToOneField"
                            else ArchitectureCardinality.MANY
                        ),
                    )
                )
                for contract_attribute_id, contract_source_id in nonempty_relationship_contracts.get(
                    (source_name, target_name), ()
                ):
                    evidence.append(
                        RelationshipEvidence(
                            id=(
                                "modwire:relationship:nonempty:"
                                f"{contract_attribute_id}:{entity_symbol.id.canonical()}:{attribute.id}"
                            ),
                            kind=ArchitectureAssertionKind.RELATIONSHIP,
                            locator=ImplementationLocator(
                                provider=self.provider,
                                coordinate=contract_attribute_id,
                                path=source_paths[contract_source_id],
                            ),
                            reference=source_name,
                            source_id=entity_ids[target.id.canonical()],
                            target_reference=target_name,
                            relationship_kind=relationship_kind,
                            source_cardinality=source_cardinality,
                            target_cardinality=ArchitectureCardinality.NONEMPTY_MANY,
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
                else self.type_reference(
                    return_types[0]
                    if return_types
                    else public_http_responses.get(callable_value.symbol_id.canonical(), "Unknown")
                )
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
        declared_members = tuple(
            cast(MemberEvidence, item) for item in evidence if item.kind == ArchitectureAssertionKind.MEMBER
        )
        classifier_symbol_by_evidence_id = {evidence_id: symbol_id for symbol_id, evidence_id in classifier_ids.items()}
        owned_member_ids = {
            f"modwire:member:attribute:{attribute.id}"
            for attribute in manifest.attributes
            if any(
                value.kind == SourceAssignedValueKind.CALL
                and value.reference.rsplit(".", maxsplit=1)[-1] == "field"
                and bool(self.call_keyword(self.assigned_call(value), "default_factory"))
                for value in attribute.assigned_values
            )
        }
        for member in declared_members:
            if member.ownership != ArchitectureMemberOwnership.INSTANCE:
                continue
            source_symbol_id = classifier_symbol_by_evidence_id[member.owner_id]
            relationship_types = (
                (member.type,)
                if member.member_kind == ArchitectureMemberKind.PROPERTY
                else (member.type, *(parameter.type for parameter in member.parameters))
            )
            relationships: set[tuple[str, ArchitectureRelationshipKind]] = set()
            for relationship_type in relationship_types:
                target_symbols = []
                for name in self.referenced_type_names(relationship_type):
                    candidates = classifiers_by_name.get(name, ())
                    if len(candidates) != 1:
                        colocated = tuple(
                            candidate
                            for candidate in candidates
                            if source_paths[str(candidate.id.source_id)] == member.locator.path
                        )
                        imported = tuple(
                            candidate
                            for candidate in candidates
                            if source_paths[str(candidate.id.source_id)]
                            in dependency_targets_by_path[member.locator.path]
                        )
                        candidates = colocated if len(colocated) == 1 else imported
                    if len(candidates) != 1:
                        continue
                    pending = [candidates[0]]
                    while pending:
                        target = pending.pop(0)
                        if target in target_symbols:
                            continue
                        target_symbols.append(target)
                        for base in bases_by_classifier[target.id.canonical()]:
                            base_candidates = classifiers_by_name.get(base, ())
                            if len(base_candidates) == 1 and base_candidates[0].id.family.value in {
                                "abstract_class",
                                "interface",
                            }:
                                pending.append(base_candidates[0])
                for target in target_symbols:
                    target_symbol_id = target.id.canonical()
                    relationship_kind = (
                        ArchitectureRelationshipKind.ASSOCIATION
                        if member.member_kind == ArchitectureMemberKind.OPERATION or target_symbol_id in enumeration_ids
                        else ArchitectureRelationshipKind.COMPOSITION
                        if source_symbol_id in pydantic_classifier_ids or member.id in owned_member_ids
                        else ArchitectureRelationshipKind.AGGREGATION
                        if relationship_type.cardinality
                        in {ArchitectureCardinality.MANY, ArchitectureCardinality.NONEMPTY_MANY}
                        else ArchitectureRelationshipKind.ASSOCIATION
                    )
                    relationships.add((target_symbol_id, relationship_kind))
                    if relationship_kind in {
                        ArchitectureRelationshipKind.AGGREGATION,
                        ArchitectureRelationshipKind.COMPOSITION,
                    }:
                        relationships.add((target_symbol_id, ArchitectureRelationshipKind.ASSOCIATION))
            for target_symbol_id, relationship_kind in sorted(
                relationships,
                key=lambda value: (value[0], value[1].value),
            ):
                evidence.append(
                    RelationshipEvidence(
                        id=(f"modwire:relationship:member:{member.id}:{target_symbol_id}:{relationship_kind.value}"),
                        kind=ArchitectureAssertionKind.RELATIONSHIP,
                        locator=member.locator,
                        reference=classifier_references[target_symbol_id],
                        source_id=member.owner_id,
                        target_reference=classifier_references[target_symbol_id],
                        relationship_kind=relationship_kind,
                        source_cardinality=ArchitectureCardinality.ONE,
                        target_cardinality=ArchitectureCardinality.ONE,
                    )
                )
        members_by_owner = {
            owner_id: tuple(values)
            for owner_id, values in groupby(
                sorted(declared_members, key=lambda item: item.owner_id),
                key=lambda item: item.owner_id,
            )
        }
        inherited_member_evidence: list[MemberEvidence] = []
        for symbol in classifier_symbols:
            symbol_id = symbol.id.canonical()
            owner_id = classifier_ids[symbol_id]
            inherited_names = list(bases_by_classifier[symbol_id])
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
            occupied = {(item.member_kind, item.name) for item in members_by_owner.get(owner_id, ())}
            for base_id in reversed(inherited_ids):
                base_owner_id = classifier_ids[base_id]
                for inherited in members_by_owner.get(base_owner_id, ()):
                    key = (inherited.member_kind, inherited.name)
                    if key in occupied:
                        continue
                    occupied.add(key)
                    inherited_member = inherited.model_copy(
                        update={
                            "id": f"{inherited.id}:inherited:{symbol_id}",
                            "owner_id": owner_id,
                        }
                    )
                    inherited_member_evidence.append(inherited_member)
                    evidence.append(inherited_member)
        for member in inherited_member_evidence:
            if (
                member.member_kind != ArchitectureMemberKind.PROPERTY
                or member.ownership != ArchitectureMemberOwnership.INSTANCE
            ):
                continue
            source_symbol_id = classifier_symbol_by_evidence_id[member.owner_id]
            relationships: set[tuple[str, ArchitectureRelationshipKind]] = set()
            for name in self.referenced_type_names(member.type):
                candidates = classifiers_by_name.get(name, ())
                if len(candidates) != 1:
                    colocated = tuple(
                        candidate
                        for candidate in candidates
                        if source_paths[str(candidate.id.source_id)] == member.locator.path
                    )
                    imported = tuple(
                        candidate
                        for candidate in candidates
                        if source_paths[str(candidate.id.source_id)] in dependency_targets_by_path[member.locator.path]
                    )
                    candidates = colocated if len(colocated) == 1 else imported
                if len(candidates) != 1:
                    continue
                target_symbol_id = candidates[0].id.canonical()
                relationship_kind = (
                    ArchitectureRelationshipKind.ASSOCIATION
                    if target_symbol_id in enumeration_ids
                    else ArchitectureRelationshipKind.COMPOSITION
                    if source_symbol_id in pydantic_classifier_ids
                    else ArchitectureRelationshipKind.AGGREGATION
                    if member.type.cardinality in {ArchitectureCardinality.MANY, ArchitectureCardinality.NONEMPTY_MANY}
                    else ArchitectureRelationshipKind.ASSOCIATION
                )
                relationships.add((target_symbol_id, relationship_kind))
                if relationship_kind in {
                    ArchitectureRelationshipKind.AGGREGATION,
                    ArchitectureRelationshipKind.COMPOSITION,
                }:
                    relationships.add((target_symbol_id, ArchitectureRelationshipKind.ASSOCIATION))
            for target_symbol_id, relationship_kind in sorted(
                relationships,
                key=lambda value: (value[0], value[1].value),
            ):
                evidence.append(
                    RelationshipEvidence(
                        id=(f"modwire:relationship:member:{member.id}:{target_symbol_id}:{relationship_kind.value}"),
                        kind=ArchitectureAssertionKind.RELATIONSHIP,
                        locator=member.locator,
                        reference=classifier_references[target_symbol_id],
                        source_id=member.owner_id,
                        target_reference=classifier_references[target_symbol_id],
                        relationship_kind=relationship_kind,
                        source_cardinality=ArchitectureCardinality.ONE,
                        target_cardinality=ArchitectureCardinality.ONE,
                    )
                )
        for relation in manifest.inheritance:
            if relation.source_symbol_id.canonical() not in classifier_ids:
                continue
            source_id = classifier_ids[relation.source_symbol_id.canonical()]
            coordinate = f"{relation.source_symbol_id.canonical()}:{relation.kind.value}:{relation.target_reference}"
            target_candidates = classifiers_by_qualified_name.get(relation.target_reference, ())
            target_leaf = relation.target_reference.rsplit(".", maxsplit=1)[-1]
            if not target_candidates and len(classifiers_by_name.get(target_leaf, ())) == 1:
                target_candidates = classifiers_by_name[target_leaf]
            target_reference = (
                classifier_references[target_candidates[0].id.canonical()]
                if len(target_candidates) == 1
                else relation.target_reference.rsplit(".", maxsplit=1)[-1]
            )
            relationship_kinds = (
                (ArchitectureRelationshipKind.REALIZATION,)
                if relation.kind.value == "implements"
                or (len(target_candidates) == 1 and target_candidates[0].id.family.value == "interface")
                else (
                    ArchitectureRelationshipKind.GENERALIZATION,
                    ArchitectureRelationshipKind.REALIZATION,
                )
                if len(target_candidates) == 1 and target_candidates[0].id.family.value == "abstract_class"
                else (ArchitectureRelationshipKind.GENERALIZATION,)
            )
            for relationship_kind in relationship_kinds:
                evidence.append(
                    RelationshipEvidence(
                        id=f"modwire:relationship:inheritance:{coordinate}:{relationship_kind.value}",
                        kind=ArchitectureAssertionKind.RELATIONSHIP,
                        locator=ImplementationLocator(
                            provider=self.provider,
                            coordinate=coordinate,
                            path=source_paths[str(relation.source_symbol_id.source_id)],
                        ),
                        reference=target_reference,
                        source_id=source_id,
                        target_reference=target_reference,
                        relationship_kind=relationship_kind,
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
                            reference=target.reference,
                            source_id=source.id,
                            target_reference=target.reference,
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
