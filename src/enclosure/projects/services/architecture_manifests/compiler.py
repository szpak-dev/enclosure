import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter
from typing import cast

from wireup import injectable

from ...errors import ProjectsError
from ..adapters.diagrams import DiagramContractsAdapter
from ..architecture_contracts.model import ArchitectureContractPublication
from .assertions.model import (
    ArchitectureAssertion,
    ArchitectureAssertionKind,
    EntityFieldAssertion,
    MemberAssertion,
    RelationshipAssertion,
)
from .compilers.base import ArchitectureDiagramCompiler
from .model import ArchitectureContractManifest, ArchitectureContractManifestUnit, ArchitectureDiagramRevision


@injectable
@dataclass(frozen=True)
class ArchitectureContractCompiler:
    diagrams: DiagramContractsAdapter
    compilers: Sequence[ArchitectureDiagramCompiler]

    def compile(self, publication: ArchitectureContractPublication) -> ArchitectureContractManifest:
        units: list[ArchitectureContractManifestUnit] = []
        ordered_compilers = tuple(sorted(self.compilers, key=attrgetter("order", "role")))
        roles = tuple(compiler.role for compiler in ordered_compilers)
        if len(roles) != len(set(roles)):
            raise ProjectsError("Architecture diagram roles must have exactly one compiler.")
        for unit in publication.units:
            assertions: list[ArchitectureAssertion] = []
            for diagram in unit.diagrams:
                candidates = tuple(compiler for compiler in ordered_compilers if compiler.role == diagram.role)
                if len(candidates) != 1:
                    raise ProjectsError(
                        f"Architecture diagram role {diagram.role.value!r} requires exactly one compiler."
                    )
                assertions.extend(candidates[0].compile(unit, diagram, self.diagrams.interpret(diagram)))
            merged: dict[str, ArchitectureAssertion] = {}
            for assertion in assertions:
                if assertion.id not in merged:
                    merged[assertion.id] = assertion
                    continue
                current = merged[assertion.id]
                current_value = current.model_dump(mode="json", exclude={"evidence", "required"})
                incoming_value = assertion.model_dump(mode="json", exclude={"evidence", "required"})
                if current_value != incoming_value:
                    raise ProjectsError(
                        f"Architecture assertion identity {assertion.id!r} has conflicting declarations."
                    )
                merged[assertion.id] = current.model_copy(
                    update={
                        "required": current.required or assertion.required,
                        "evidence": tuple(
                            sorted(
                                set(current.evidence + assertion.evidence),
                                key=attrgetter("diagram_id", "diagram_revision", "element_id"),
                            )
                        ),
                    }
                )
            ordered = tuple(sorted(merged.values(), key=lambda item: (item.kind.value, item.id)))
            subjects = {assertion.subject_id for assertion in ordered}
            classifiers = {
                assertion.subject_id for assertion in ordered if assertion.kind == ArchitectureAssertionKind.CLASSIFIER
            }
            entities = {
                assertion.subject_id for assertion in ordered if assertion.kind == ArchitectureAssertionKind.ENTITY
            }
            for assertion in ordered:
                if assertion.kind == ArchitectureAssertionKind.MEMBER:
                    owner_id = cast(MemberAssertion, assertion).owner_id
                    if owner_id not in classifiers:
                        raise ProjectsError(f"Architecture member {assertion.id!r} has no owning classifier.")
                if assertion.kind == ArchitectureAssertionKind.ENTITY_FIELD:
                    owner_id = cast(EntityFieldAssertion, assertion).owner_id
                    if owner_id not in entities:
                        raise ProjectsError(f"Architecture entity field {assertion.id!r} has no owning entity.")
                if assertion.kind == ArchitectureAssertionKind.RELATIONSHIP:
                    relationship = cast(RelationshipAssertion, assertion)
                    if relationship.source_id not in subjects or relationship.target_id not in subjects:
                        raise ProjectsError(
                            f"Architecture relationship {assertion.id!r} must connect declared subjects."
                        )
            units.append(
                ArchitectureContractManifestUnit(
                    key=unit.key,
                    source_root=unit.source_root,
                    coverage=unit.coverage,
                    diagram_revisions=tuple(
                        ArchitectureDiagramRevision(
                            diagram_id=diagram.diagram_id,
                            diagram_revision=diagram.diagram_revision,
                        )
                        for diagram in unit.diagrams
                    ),
                    exclusions=unit.exclusions,
                    assertions=ordered,
                )
            )
        ordered_units = tuple(sorted(units, key=attrgetter("key")))
        payload = {
            "schema_version": 3,
            "project_id": publication.project_id,
            "publication_id": publication.id,
            "publication_version": publication.version,
            "publication_revision": publication.revision,
            "units": [unit.model_dump(mode="json") for unit in ordered_units],
            "digest_algorithm": "sha256",
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureContractManifest(
            schema_version=3,
            project_id=publication.project_id,
            publication_id=publication.id,
            publication_version=publication.version,
            publication_revision=publication.revision,
            units=ordered_units,
            digest_algorithm="sha256",
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )
