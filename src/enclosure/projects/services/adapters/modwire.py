from collections.abc import Mapping
from dataclasses import dataclass

from modwire.application import ImplementationManifestDocument, ModwireApplication
from wireup import injectable

from ...errors import ProjectsError
from ..architecture_manifests.facts.model import ArchitectureFactCapability
from ..architecture_manifests.model import ArchitectureSupportState
from ..architecture_manifests.observed.model import (
    ObservedAnnotationFact,
    ObservedAttributeFact,
    ObservedCallableFact,
    ObservedCapability,
    ObservedDependencyFact,
    ObservedImplementationFact,
    ObservedImplementationManifest,
    ObservedInheritanceFact,
    ObservedParameterFact,
    ObservedSourceFact,
    ObservedSymbolFact,
)


@injectable
@dataclass(frozen=True)
class ModwireManifestAdapter:
    def read(self, document: Mapping[str, object]) -> ObservedImplementationManifest:
        application = ModwireApplication.create()
        artifact = ImplementationManifestDocument.model_validate(document)
        if artifact.format not in application.implementation_manifest_formats():
            raise ProjectsError(f"Modwire manifest format {artifact.format.id!r} is not registered.")
        manifest = application.read_implementation_manifest(artifact)
        source_paths = {str(source.source_id): source.relative_path for source in manifest.source_manifest.sources}
        symbol_targets = {
            symbol.id.canonical(): (
                f"symbol:{source_paths[str(symbol.id.source_id)]}::{symbol.id.family.value}:{symbol.qualified_name}"
            )
            for symbol in manifest.symbols
        }
        parameter_targets = {
            parameter.id: (
                f"parameter:{symbol_targets[parameter.callable_id.canonical()]}:{parameter.position}:{parameter.name}"
            )
            for parameter in manifest.parameters
        }
        annotation_targets = symbol_targets | parameter_targets
        parameter_annotations = {
            parameter.id: tuple(
                annotation.expression
                for annotation in manifest.annotations
                if annotation.target_id == parameter.id and annotation.role == "parameter_type"
            )
            for parameter in manifest.parameters
        }

        facts: list[ObservedImplementationFact] = []
        facts.extend(
            ObservedSourceFact(
                id=f"source:{source.relative_path}",
                capability=ArchitectureFactCapability.SOURCES,
                path=source.relative_path,
                content_digest=source.content_digest,
            )
            for source in manifest.source_manifest.sources
        )
        facts.extend(
            ObservedSymbolFact(
                id=symbol_targets[symbol.id.canonical()],
                capability=ArchitectureFactCapability.SYMBOLS,
                path=source_paths[str(symbol.id.source_id)],
                family=symbol.id.family.value,
                qualified_name=symbol.qualified_name,
                kind=symbol.kind,
                visibility=symbol.visibility,
            )
            for symbol in manifest.symbols
        )
        facts.extend(
            ObservedCallableFact(
                id=f"callable:{symbol_targets[callable_value.symbol_id.canonical()]}",
                capability=ArchitectureFactCapability.CALLABLES,
                owner_id=symbol_targets[callable_value.symbol_id.canonical()],
                callable_kind=callable_value.callable_kind,
            )
            for callable_value in manifest.callables
        )
        facts.extend(
            ObservedParameterFact(
                id=(
                    f"parameter:{symbol_targets[parameter.callable_id.canonical()]}:"
                    f"{parameter.position}:{parameter.name}"
                ),
                capability=ArchitectureFactCapability.PARAMETERS,
                owner_id=symbol_targets[parameter.callable_id.canonical()],
                position=parameter.position,
                name=parameter.name,
                kind=parameter.kind,
                has_default=parameter.has_default,
                annotations=parameter_annotations[parameter.id],
            )
            for parameter in manifest.parameters
        )
        facts.extend(
            ObservedAttributeFact(
                id=f"attribute:{symbol_targets[attribute.owner_symbol_id.canonical()]}:{attribute.name}",
                capability=ArchitectureFactCapability.ATTRIBUTES,
                owner_id=symbol_targets[attribute.owner_symbol_id.canonical()],
                name=attribute.name,
                optional=attribute.is_optional,
            )
            for attribute in manifest.attributes
        )
        facts.extend(
            ObservedAnnotationFact(
                id=f"annotation:{annotation_targets[annotation.target_id]}:{annotation.role}:{annotation.expression}",
                capability=ArchitectureFactCapability.ANNOTATIONS,
                target_id=annotation_targets[annotation.target_id],
                role=annotation.role,
                expression=annotation.expression,
            )
            for annotation in manifest.annotations
        )
        facts.extend(
            ObservedInheritanceFact(
                id=(
                    f"inheritance:{symbol_targets[relation.source_symbol_id.canonical()]}:"
                    f"{relation.kind}:{relation.target_reference}"
                ),
                capability=ArchitectureFactCapability.INHERITANCE,
                owner_id=symbol_targets[relation.source_symbol_id.canonical()],
                kind=relation.kind,
                target=relation.target_reference,
            )
            for relation in manifest.inheritance
        )
        facts.extend(
            ObservedDependencyFact(
                id=(
                    f"dependency:{source_paths[dependency.source_id]}:"
                    f"{source_paths[dependency.target] if dependency.target_kind == 'source' else dependency.target}:"
                    f"{dependency.kind}:{dependency.specifier}"
                ),
                capability=ArchitectureFactCapability.DEPENDENCIES,
                source_path=source_paths[dependency.source_id],
                kind=dependency.kind,
                target=(source_paths[dependency.target] if dependency.target_kind == "source" else dependency.target),
                specifier=dependency.specifier,
                resolution=dependency.resolution,
            )
            for dependency in manifest.dependencies
        )
        capabilities = tuple(
            ObservedCapability(
                capability=ArchitectureFactCapability(coverage.capability.value),
                support=ArchitectureSupportState(coverage.status.value),
                explanation=coverage.explanation,
            )
            for coverage in manifest.producer.capabilities
        )
        return ObservedImplementationManifest(
            schema_version=manifest.schema_version,
            document_digest=artifact.digest,
            source_digest=manifest.source_manifest.digest,
            modwire_version=manifest.producer.modwire_version,
            extractor_id=manifest.producer.extractor.id,
            language=manifest.producer.extractor.language,
            capabilities=capabilities,
            facts=tuple(sorted(facts, key=lambda fact: (fact.capability.value, fact.id))),
        )
