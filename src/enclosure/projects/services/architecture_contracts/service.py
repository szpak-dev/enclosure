import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

from wireup import injectable

from ...errors import ProjectsError
from ..adapters import DiagramContractsAdapter, ResolvedArchitectureDiagram
from .model import (
    ArchitectureContractPublication,
    ArchitectureContractUnitInput,
    ArchitectureDiagramRole,
    ArchitectureDiagramScope,
)
from .repository import ArchitectureContractRepository


@injectable
@dataclass(frozen=True)
class ArchitectureContractsService:
    diagrams: DiagramContractsAdapter
    repository: ArchitectureContractRepository

    def publish(
        self,
        project_id: str,
        units: tuple[ArchitectureContractUnitInput, ...],
    ) -> ArchitectureContractPublication:
        if not units:
            raise ProjectsError("An architecture contract requires at least one contract unit.")

        unit_keys: set[str] = set()
        diagram_ids: set[str] = set()
        resolved_units: list[tuple[ArchitectureContractUnitInput, tuple[ResolvedArchitectureDiagram, ...]]] = []
        for unit in units:
            if not unit.key or unit.key != unit.key.strip():
                raise ProjectsError("Architecture contract unit keys must be non-empty and normalized.")
            if unit.key in unit_keys:
                raise ProjectsError(f"Architecture contract unit key {unit.key!r} is duplicated.")
            unit_keys.add(unit.key)
            if not unit.diagram_set_id or unit.diagram_set_id != unit.diagram_set_id.strip():
                raise ProjectsError("Architecture contract diagram-set identifiers must be non-empty and normalized.")
            if not unit.source_root or "\\" in unit.source_root:
                raise ProjectsError(f"Architecture source root {unit.source_root!r} is not a normalized relative path.")
            source_root = PurePosixPath(unit.source_root)
            if source_root.is_absolute() or ".." in source_root.parts or str(source_root) != unit.source_root:
                raise ProjectsError(f"Architecture source root {unit.source_root!r} is not a normalized relative path.")
            if not unit.diagrams:
                raise ProjectsError(f"Architecture contract unit {unit.key!r} requires diagrams.")

            tree_members = tuple(member for member in unit.diagrams if member.role == ArchitectureDiagramRole.TREE)
            if len(tree_members) != 1:
                raise ProjectsError(f"Architecture contract unit {unit.key!r} requires exactly one Tree diagram.")
            if tree_members[0].scope == ArchitectureDiagramScope.REFERENCE:
                raise ProjectsError(
                    f"Architecture contract unit {unit.key!r} cannot use a reference-only Tree diagram."
                )
            owning_uml = tuple(
                member
                for member in unit.diagrams
                if member.role == ArchitectureDiagramRole.UML and member.scope != ArchitectureDiagramScope.REFERENCE
            )
            if not owning_uml:
                raise ProjectsError(
                    f"Architecture contract unit {unit.key!r} requires at least one owning UML diagram."
                )

            exclusion_paths: set[str] = set()
            for exclusion in unit.exclusions:
                if not exclusion.path or "\\" in exclusion.path:
                    raise ProjectsError(f"Architecture exclusion {exclusion.path!r} is not a normalized relative path.")
                exclusion_path = PurePosixPath(exclusion.path)
                if (
                    exclusion_path.is_absolute()
                    or ".." in exclusion_path.parts
                    or str(exclusion_path) != exclusion.path
                    or exclusion.path == "."
                ):
                    raise ProjectsError(f"Architecture exclusion {exclusion.path!r} is not a normalized relative path.")
                if exclusion.path in exclusion_paths:
                    raise ProjectsError(
                        f"Architecture exclusion {exclusion.path!r} is duplicated in unit {unit.key!r}."
                    )
                if not exclusion.reason or exclusion.reason != exclusion.reason.strip():
                    raise ProjectsError(f"Architecture exclusion {exclusion.path!r} requires a normalized rationale.")
                exclusion_paths.add(exclusion.path)

            resolved_diagrams = []
            supported_kinds = {
                ArchitectureDiagramRole.TREE: "treeView-beta",
                ArchitectureDiagramRole.UML: "classDiagram",
                ArchitectureDiagramRole.ENTITY: "erDiagram",
            }
            for member in unit.diagrams:
                if member.diagram_id in diagram_ids:
                    raise ProjectsError(f"Architecture diagram {member.diagram_id!r} is duplicated in the publication.")
                diagram_ids.add(member.diagram_id)
                resolved = self.diagrams.resolve(
                    unit.diagram_set_id,
                    member.diagram_id,
                    member.expected_revision,
                )
                if resolved.draft:
                    raise ProjectsError(f"Architecture diagram {member.diagram_id!r} is still a draft.")
                expected_kind = supported_kinds[member.role]
                if resolved.kind != expected_kind:
                    raise ProjectsError(
                        f"Architecture diagram {member.diagram_id!r} has kind {resolved.kind!r}; "
                        f"role {member.role.value!r} requires {expected_kind!r}."
                    )
                resolved_diagrams.append(resolved)
            resolved_units.append((unit, tuple(resolved_diagrams)))

        authority = f"project:{project_id}:architecture-contract"
        canonical_units = []
        for unit, resolved_diagrams in resolved_units:
            canonical_units.append(
                {
                    "key": unit.key,
                    "diagram_set_id": unit.diagram_set_id,
                    "source_root": unit.source_root,
                    "coverage": unit.coverage.value,
                    "diagrams": [
                        {
                            "diagram_id": resolved.diagram_id,
                            "diagram_revision": resolved.revision,
                            "role": member.role.value,
                            "scope": member.scope.value,
                            "kind": resolved.kind,
                            "snapshot_version": resolved.snapshot_version,
                            "registry_fingerprint": resolved.registry_fingerprint,
                            "snapshot_digest": resolved.snapshot_digest,
                            "snapshot": resolved.snapshot,
                        }
                        for member, resolved in zip(unit.diagrams, resolved_diagrams, strict=True)
                    ],
                    "exclusions": [exclusion.model_dump(mode="json") for exclusion in unit.exclusions],
                }
            )
        canonical = json.dumps(
            {
                "project_id": project_id,
                "authority": authority,
                "units": canonical_units,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        revision = sha256(canonical.encode("utf-8")).hexdigest()
        return self.repository.publish(project_id, authority, revision, tuple(resolved_units))

    def get(self, project_id: str, publication_id: str) -> ArchitectureContractPublication:
        return self.repository.get(project_id, publication_id)
