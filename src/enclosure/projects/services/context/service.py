from collections import defaultdict
from dataclasses import dataclass

from wireup import injectable

from ..adapters import RecordsAdapter, WorkspaceGuidance
from ..contracts.model import (
    ConfiguredOperatingContractBinding,
    UnconfiguredOperatingContractBinding,
)
from .model import (
    WorkspaceAuthority,
    WorkspaceContext,
    WorkspaceContextDiagnostic,
)


@injectable
@dataclass(frozen=True)
class WorkspaceContextService:
    records: RecordsAdapter

    def resolve(
        self,
        project_id: str,
        root: str,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
        task: str,
    ) -> WorkspaceContext:
        if isinstance(binding, UnconfiguredOperatingContractBinding):
            return WorkspaceContext(
                project_id=project_id,
                root=root,
                readiness="incomplete",
                authority=WorkspaceAuthority(
                    kind="project-operating-contract",
                    id=f"project:{project_id}:operating-contract",
                    revision="unconfigured",
                ),
                guidance=(),
                diagnostics=(
                    WorkspaceContextDiagnostic(
                        code="mandatory_contract_unconfigured",
                        message="The project has no operating contract. Publish and bind one before continuing.",
                        guidance_ids=(),
                    ),
                ),
            )

        guidance_references = tuple(
            reference for reference in binding.effective_revision.references if reference.kind == "guidance"
        )
        record_ids = tuple(reference.id for reference in guidance_references)
        resolution = self.records.resolve_guidance(record_ids, task)
        diagnostics = self._diagnostics(
            record_ids,
            resolution.guidance,
            resolution.selected_ids,
            resolution.missing_ids,
            {reference.id: reference.revision for reference in guidance_references},
        )
        guidance_by_id = {guidance.id: guidance for guidance in resolution.guidance}
        selected_guidance = tuple(
            guidance_by_id[guidance_id] for guidance_id in resolution.selected_ids if guidance_id in guidance_by_id
        )
        readiness = "conflicted" if self._has_conflict(diagnostics) else "incomplete" if diagnostics else "ready"
        return WorkspaceContext(
            project_id=project_id,
            root=root,
            readiness=readiness,
            authority=WorkspaceAuthority(
                kind="project-operating-contract",
                id=binding.contract.authority,
                revision=str(binding.effective_revision.version),
            ),
            guidance=selected_guidance,
            diagnostics=diagnostics,
        )

    def _diagnostics(
        self,
        record_ids: tuple[str, ...],
        guidance: tuple[WorkspaceGuidance, ...],
        selected_ids: tuple[str, ...],
        missing_ids: tuple[str, ...],
        expected_revisions: dict[str, str],
    ) -> tuple[WorkspaceContextDiagnostic, ...]:
        diagnostics = []
        if not record_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="mandatory_guidance_missing",
                    message=(
                        "The project has no bound guidance. Bind required guidance before treating context as ready."
                    ),
                    guidance_ids=(),
                )
            )
        if missing_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="mandatory_guidance_unavailable",
                    message="One or more bound guidance records no longer exist. Rebind or restore them.",
                    guidance_ids=tuple(sorted(missing_ids)),
                )
            )

        stale_ids = tuple(sorted(item.id for item in guidance if item.schema_revision != item.current_schema_revision))
        if stale_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_revision_stale",
                    message="Bound guidance uses an obsolete category schema revision. Review and republish it.",
                    guidance_ids=stale_ids,
                )
            )
        changed_ids = tuple(
            sorted(item.id for item in guidance if expected_revisions.get(item.id, item.revision) != item.revision)
        )
        if changed_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_revision_changed",
                    message="Published operating-contract guidance has changed. Publish a new contract revision.",
                    guidance_ids=changed_ids,
                )
            )
        if guidance and not selected_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_selection_unavailable",
                    message="Bound guidance exists but no safe task selection could be produced.",
                    guidance_ids=tuple(sorted(item.id for item in guidance)),
                )
            )

        authorities: defaultdict[str, list[str]] = defaultdict(list)
        for item in guidance:
            authorities[item.authority].append(item.id)
        for authority, guidance_ids in sorted(authorities.items()):
            if len(guidance_ids) < 2:
                continue
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_authority_conflict",
                    message=(
                        f"Multiple bound guidance records claim authority {authority!r}. Bind one effective source."
                    ),
                    guidance_ids=tuple(sorted(guidance_ids)),
                )
            )
        return tuple(diagnostics)

    def _has_conflict(self, diagnostics: tuple[WorkspaceContextDiagnostic, ...]) -> bool:
        return any(diagnostic.code == "guidance_authority_conflict" for diagnostic in diagnostics)
