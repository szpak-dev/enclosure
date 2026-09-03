from dataclasses import dataclass

from wireup import injectable

from ... import models
from ...errors import ProjectsError
from ..adapters.records import RecordsAdapter
from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from ..routing.service import WorkspaceRoutingService
from .model import (
    GuidanceGraph,
    GuidanceNode,
    GuidanceRelationship,
    GuidanceRelationshipInput,
    GuidanceRelationshipKind,
    GuidanceRequirement,
)
from .repository import GuidanceRelationshipRepository


@injectable
@dataclass(frozen=True)
class GuidanceGraphService:
    records: RecordsAdapter
    routing: WorkspaceRoutingService
    repository: GuidanceRelationshipRepository

    def find_relationships(self, project_id: str) -> tuple[GuidanceRelationship, ...]:
        return tuple(self._relationship(relationship) for relationship in self.repository.find(project_id))

    def replace_relationships(
        self,
        project_id: str,
        relationships: tuple[GuidanceRelationshipInput, ...],
    ) -> tuple[GuidanceRelationship, ...]:
        identities = tuple(
            (relationship.source_record_id, relationship.target_record_id, relationship.kind)
            for relationship in relationships
        )
        if len(identities) != len(set(identities)):
            raise ProjectsError("A guidance relationship cannot be declared more than once.")
        self.records.check_records_existence(
            tuple(
                dict.fromkeys(
                    record_id
                    for relationship in relationships
                    for record_id in (relationship.source_record_id, relationship.target_record_id)
                )
            )
        )
        return tuple(
            self._relationship(relationship) for relationship in self.repository.replace(project_id, relationships)
        )

    def build(
        self,
        project_id: str,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
    ) -> GuidanceGraph:
        entry_point_ids = (
            ()
            if isinstance(binding, UnconfiguredOperatingContractBinding)
            else tuple(
                reference.id for reference in binding.effective_revision.references if reference.kind == "guidance"
            )
        )
        supplemental_ids = tuple(
            scope.record_id for scope in self.routing.find_scopes(project_id) if scope.record_id not in entry_point_ids
        )
        effective_ids = (*entry_point_ids, *supplemental_ids)
        resolution = self.records.resolve_guidance(effective_ids)
        mandatory_ids = set(entry_point_ids)
        return GuidanceGraph(
            project_id=project_id,
            nodes=tuple(
                GuidanceNode(
                    guidance=guidance,
                    requirement=(
                        GuidanceRequirement.MANDATORY
                        if guidance.id in mandatory_ids
                        else GuidanceRequirement.SUPPLEMENTAL
                    ),
                )
                for guidance in resolution.guidance
            ),
            entry_point_ids=entry_point_ids,
            relationships=self.find_relationships(project_id),
            missing_record_ids=resolution.missing_ids,
        )

    def _relationship(self, relationship: models.GuidanceRelationship) -> GuidanceRelationship:
        return GuidanceRelationship(
            id=relationship.id,
            project_id=relationship.project_id,
            source_record_id=relationship.source_record_id,
            target_record_id=relationship.target_record_id,
            kind=GuidanceRelationshipKind(relationship.kind),
        )
