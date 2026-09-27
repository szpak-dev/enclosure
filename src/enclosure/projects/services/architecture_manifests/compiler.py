import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter
from typing import cast

from wireup import injectable

from ...errors import ProjectsError
from ..adapters.diagrams import DiagramContractsAdapter
from ..architecture_contracts.model import (
    ArchitectureContractPublication,
    ArchitectureDiagramRole,
    ArchitectureDiagramScope,
)
from .compilers.base import ArchitectureDiagramCompiler
from .facts.model import (
    ArchitectureContractFact,
    ArchitectureFactCapability,
    AnnotationContractFact,
    AttributeContractFact,
    CallableContractFact,
    DependencyContractFact,
    InheritanceContractFact,
    ParameterContractFact,
    SourceContractFact,
    SymbolContractFact,
)
from .model import ArchitectureContractManifest, ArchitectureContractManifestUnit


@injectable
@dataclass(frozen=True)
class ArchitectureContractCompiler:
    diagrams: DiagramContractsAdapter
    compilers: Sequence[ArchitectureDiagramCompiler]

    def compile(self, publication: ArchitectureContractPublication) -> ArchitectureContractManifest:
        units: list[ArchitectureContractManifestUnit] = []
        ordered_compilers = tuple(sorted(self.compilers, key=attrgetter("order", "role")))
        for unit in publication.units:
            unit_facts: list[ArchitectureContractFact] = []
            interpreted = tuple((diagram, self.diagrams.interpret(diagram)) for diagram in unit.diagrams)
            all_uml_symbol_ids = {
                symbol.element_id
                for diagram, semantics in interpreted
                if diagram.role == ArchitectureDiagramRole.UML
                for symbol in semantics.symbols
            }
            asserted_uml_symbol_ids = {
                symbol.element_id
                for diagram, semantics in interpreted
                if diagram.role == ArchitectureDiagramRole.UML and diagram.scope != ArchitectureDiagramScope.REFERENCE
                for symbol in semantics.symbols
            }
            for diagram, semantics in interpreted:
                if diagram.role == ArchitectureDiagramRole.ENTITY:
                    entity_symbol_ids = {symbol.element_id for symbol in semantics.symbols}
                    relation_symbol_ids = {
                        symbol_id
                        for relation in semantics.relations
                        for symbol_id in (relation.source_id, relation.target_id)
                    }
                    if diagram.scope == ArchitectureDiagramScope.REFERENCE:
                        owning_uml_symbol_ids = all_uml_symbol_ids
                    else:
                        owning_uml_symbol_ids = asserted_uml_symbol_ids
                    unresolved = sorted((entity_symbol_ids | relation_symbol_ids) - owning_uml_symbol_ids)
                    if unresolved:
                        raise ProjectsError(
                            f"Entity diagram {diagram.diagram_id!r} has identities absent from owning UML: "
                            f"{', '.join(unresolved)}."
                        )
            for diagram, semantics in interpreted:
                candidates = tuple(compiler for compiler in ordered_compilers if compiler.role == diagram.role)
                if len(candidates) != 1:
                    raise ProjectsError(
                        f"Architecture diagram role {diagram.role.value!r} requires exactly one manifest compiler."
                    )
                unit_facts.extend(candidates[0].compile(unit, diagram, semantics))
            merged: dict[str, ArchitectureContractFact] = {}
            for fact in unit_facts:
                if fact.id not in merged:
                    merged[fact.id] = fact
                else:
                    current = merged[fact.id]
                    current_value = current.model_dump(mode="json", exclude={"evidence", "required"})
                    incoming_value = fact.model_dump(mode="json", exclude={"evidence", "required"})
                    if current_value != incoming_value:
                        raise ProjectsError(f"Architecture fact identity {fact.id!r} has conflicting declarations.")
                    evidence = tuple(
                        sorted(
                            set(current.evidence + fact.evidence),
                            key=attrgetter("diagram_id", "diagram_revision", "element_id"),
                        )
                    )
                    merged[fact.id] = current.model_copy(
                        update={
                            "required": current.required or fact.required,
                            "evidence": evidence,
                        }
                    )
            facts = tuple(sorted(merged.values(), key=lambda fact: (fact.capability.value, fact.id)))
            sources = {
                cast(SourceContractFact, fact).path
                for fact in facts
                if fact.capability == ArchitectureFactCapability.SOURCES
            }
            symbols = {
                fact.id: cast(SymbolContractFact, fact)
                for fact in facts
                if fact.capability == ArchitectureFactCapability.SYMBOLS
            }
            attributes = {
                fact.id: cast(AttributeContractFact, fact)
                for fact in facts
                if fact.capability == ArchitectureFactCapability.ATTRIBUTES
            }
            for symbol in symbols.values():
                if symbol.path not in sources:
                    raise ProjectsError(
                        f"Architecture symbol {symbol.id!r} in unit {unit.key!r} has no Tree source declaration."
                    )
            for fact in facts:
                if fact.capability == ArchitectureFactCapability.CALLABLES:
                    owner_id = cast(CallableContractFact, fact).owner_id
                    if owner_id not in symbols:
                        raise ProjectsError(f"Architecture callable {fact.id!r} has no owning UML symbol.")
                if fact.capability == ArchitectureFactCapability.PARAMETERS:
                    owner_id = cast(ParameterContractFact, fact).owner_id
                    if owner_id not in symbols:
                        raise ProjectsError(f"Architecture parameter {fact.id!r} has no owning UML callable symbol.")
                if fact.capability == ArchitectureFactCapability.ATTRIBUTES:
                    owner_id = cast(AttributeContractFact, fact).owner_id
                    if owner_id not in symbols:
                        raise ProjectsError(f"Architecture attribute {fact.id!r} has no owning UML symbol.")
                if fact.capability == ArchitectureFactCapability.ANNOTATIONS:
                    target_id = cast(AnnotationContractFact, fact).target_id
                    if target_id not in symbols and target_id not in attributes:
                        raise ProjectsError(f"Architecture annotation {fact.id!r} has no owning UML fact.")
                if fact.capability == ArchitectureFactCapability.INHERITANCE:
                    owner_id = cast(InheritanceContractFact, fact).owner_id
                    if owner_id not in symbols:
                        raise ProjectsError(f"Architecture inheritance {fact.id!r} has no owning UML symbol.")
                if fact.capability == ArchitectureFactCapability.DEPENDENCIES:
                    dependency = cast(DependencyContractFact, fact)
                    if dependency.source_path not in sources or dependency.target not in sources:
                        raise ProjectsError(
                            f"Architecture dependency {fact.id!r} must connect sources declared by the Tree diagram."
                        )
            units.append(
                ArchitectureContractManifestUnit(
                    key=unit.key,
                    source_root=unit.source_root,
                    coverage=unit.coverage,
                    exclusions=unit.exclusions,
                    facts=facts,
                )
            )
        ordered_units = tuple(sorted(units, key=attrgetter("key")))
        payload = {
            "schema_version": 1,
            "project_id": publication.project_id,
            "publication_id": publication.id,
            "publication_version": publication.version,
            "publication_revision": publication.revision,
            "units": [unit.model_dump(mode="json") for unit in ordered_units],
            "digest_algorithm": "sha256",
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return ArchitectureContractManifest(
            schema_version=1,
            project_id=publication.project_id,
            publication_id=publication.id,
            publication_version=publication.version,
            publication_revision=publication.revision,
            units=ordered_units,
            digest_algorithm="sha256",
            digest=digest,
        )
