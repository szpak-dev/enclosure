from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..adapters.model import WorkspaceGuidance
from ..contracts.model import (
    ConfiguredOperatingContractBinding,
    UnconfiguredOperatingContractBinding,
)
from ..receipts.model import WorkspaceAuthority, WorkspaceContextDiagnostic
from ..receipts.service import ContextReceiptService
from ..routing.model import GuidanceRoute
from ..routing.service import WorkspaceRoutingService
from .model import WorkspaceContext


@injectable
@dataclass(frozen=True)
class WorkspaceContextService:
    routing: WorkspaceRoutingService
    receipts: ContextReceiptService
    max_optional_characters: int = field(default=4096, init=False)

    def resolve(
        self,
        project_id: str,
        root: str,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
        task: str,
    ) -> WorkspaceContext:
        if isinstance(binding, UnconfiguredOperatingContractBinding):
            route = GuidanceRoute(
                items=(),
                missing_mandatory_ids=(),
                omitted_optional_ids=(),
                used_optional_characters=0,
                optional_character_limit=self.max_optional_characters,
            )
            authority = WorkspaceAuthority(
                kind="project-operating-contract",
                id=f"project:{project_id}:operating-contract",
                revision="unconfigured",
                provenance="unconfigured",
            )
            diagnostics = (
                WorkspaceContextDiagnostic(
                    code="mandatory_contract_unconfigured",
                    message="The project has no operating contract. Publish and bind one before continuing.",
                    guidance_ids=(),
                ),
            )
            return WorkspaceContext(
                project_id=project_id,
                root=root,
                readiness="incomplete",
                guidance=(),
                receipt=self.receipts.build(route, authority, diagnostics, "incomplete"),
            )

        guidance_references = tuple(
            reference for reference in binding.effective_revision.references if reference.kind == "guidance"
        )
        record_ids = tuple(reference.id for reference in guidance_references)
        route = self.routing.route(
            project_id,
            guidance_references,
            task,
            self.max_optional_characters,
        )
        guidance = tuple(item.guidance for item in route.items)
        mandatory_guidance = tuple(item.guidance for item in route.items if item.requirement == "mandatory")
        diagnostics = self._diagnostics(
            record_ids,
            mandatory_guidance,
            guidance,
            route.missing_mandatory_ids,
            {reference.id: reference.revision for reference in guidance_references},
        )
        readiness = "conflicted" if self._has_conflict(diagnostics) else "incomplete" if diagnostics else "ready"
        authority = WorkspaceAuthority(
            kind="project-operating-contract",
            id=binding.contract.authority,
            revision=str(binding.effective_revision.version),
            provenance=binding.contract.provenance,
        )
        return WorkspaceContext(
            project_id=project_id,
            root=root,
            readiness=readiness,
            guidance=guidance,
            receipt=self.receipts.build(route, authority, diagnostics, readiness),
        )

    def _diagnostics(
        self,
        record_ids: tuple[str, ...],
        mandatory_guidance: tuple[WorkspaceGuidance, ...],
        guidance: tuple[WorkspaceGuidance, ...],
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

        stale_ids = tuple(
            sorted(item.id for item in mandatory_guidance if item.schema_revision != item.current_schema_revision)
        )
        if stale_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_revision_stale",
                    message="Bound guidance uses an obsolete category schema revision. Review and republish it.",
                    guidance_ids=stale_ids,
                )
            )
        changed_ids = tuple(
            sorted(
                item.id
                for item in mandatory_guidance
                if expected_revisions.get(item.id, item.revision) != item.revision
            )
        )
        if changed_ids:
            diagnostics.append(
                WorkspaceContextDiagnostic(
                    code="guidance_revision_changed",
                    message="Published operating-contract guidance has changed. Publish a new contract revision.",
                    guidance_ids=changed_ids,
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
