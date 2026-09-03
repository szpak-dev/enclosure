from dataclasses import dataclass

from wireup import injectable

from ... import models
from ...errors import ProjectsError
from ..adapters.records import RecordsAdapter
from ..contracts.model import OperatingContractReference
from .applicability import GuidanceApplicabilityService
from .budget import GuidanceBudgetService
from .model import GuidanceCandidate, GuidanceRoute, GuidanceRouteItem, GuidanceScope
from .ordering import GuidanceOrderingService
from .repository import GuidanceScopeRepository


@injectable
@dataclass(frozen=True)
class WorkspaceRoutingService:
    records: RecordsAdapter
    repository: GuidanceScopeRepository
    applicability: GuidanceApplicabilityService
    ordering: GuidanceOrderingService
    budget: GuidanceBudgetService

    def find_scopes(self, project_id: str) -> tuple[GuidanceScope, ...]:
        return tuple(self._scope(scope) for scope in self.repository.find(project_id))

    def replace_scopes(self, project_id: str, record_ids: tuple[str, ...]) -> tuple[GuidanceScope, ...]:
        if len(record_ids) != len(set(record_ids)):
            raise ProjectsError("A guidance scope cannot reference a record more than once.")
        self.records.check_records_existence(record_ids)
        return tuple(self._scope(scope) for scope in self.repository.replace(project_id, record_ids))

    def route(
        self,
        project_id: str,
        mandatory_references: tuple[OperatingContractReference, ...],
        task: str,
        max_optional_characters: int,
    ) -> GuidanceRoute:
        mandatory_ids = tuple(reference.id for reference in mandatory_references if reference.kind == "guidance")
        mandatory_resolution = self.records.resolve_guidance(mandatory_ids)
        mandatory_by_id = {guidance.id: guidance for guidance in mandatory_resolution.guidance}
        mandatory = tuple(mandatory_by_id[record_id] for record_id in mandatory_ids if record_id in mandatory_by_id)

        scopes = tuple(scope for scope in self.find_scopes(project_id) if scope.record_id not in mandatory_by_id)
        optional_resolution = self.records.resolve_guidance(tuple(scope.record_id for scope in scopes))
        optional_by_id = {guidance.id: guidance for guidance in optional_resolution.guidance}
        candidates = tuple(
            GuidanceCandidate(guidance=optional_by_id[scope.record_id], position=scope.position)
            for scope in scopes
            if scope.record_id in optional_by_id
        )
        applicable = self.applicability.filter(task, candidates)
        ranking = self.records.rank_guidance(
            tuple(candidate.guidance.id for candidate in applicable),
            task,
        )
        ordered = self.ordering.order(applicable, ranking)
        budget = self.budget.select(ordered, max_optional_characters)
        return GuidanceRoute(
            items=(
                *(
                    GuidanceRouteItem(
                        guidance=guidance,
                        requirement="mandatory",
                        reason="operating-contract",
                    )
                    for guidance in mandatory
                ),
                *(
                    GuidanceRouteItem(
                        guidance=candidate.guidance,
                        requirement="supplemental",
                        reason="task-applicable" if candidate.guidance.applies_when else "project-default",
                    )
                    for candidate in budget.selected
                ),
            ),
            missing_mandatory_ids=mandatory_resolution.missing_ids,
            omitted_optional_ids=budget.omitted_ids,
            used_optional_characters=budget.used_characters,
            optional_character_limit=budget.limit_characters,
        )

    def _scope(self, scope: models.GuidanceScope) -> GuidanceScope:
        return GuidanceScope(
            id=scope.id,
            project_id=scope.project_id,
            record_id=scope.record_id,
            position=scope.position,
        )
