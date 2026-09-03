from dataclasses import dataclass
from typing import Literal

from wireup import injectable

from ..routing.model import GuidanceRoute
from .model import (
    ContextBudget,
    ContextCoverage,
    ContextOmission,
    ContextReceipt,
    ReceiptItem,
    WorkspaceAuthority,
    WorkspaceContextDiagnostic,
)


@injectable
@dataclass(frozen=True)
class ContextReceiptService:
    def build(
        self,
        route: GuidanceRoute,
        authority: WorkspaceAuthority,
        diagnostics: tuple[WorkspaceContextDiagnostic, ...],
        readiness: Literal["ready", "incomplete", "conflicted"],
    ) -> ContextReceipt:
        explanations = {
            "operating-contract": "Required by the active project operating contract.",
            "task-applicable": "Matched the current task through its applicability conditions.",
            "project-default": "Applies to every task in this project.",
        }
        items = tuple(
            ReceiptItem(
                record_id=item.guidance.id,
                title=item.guidance.title,
                requirement=item.requirement,
                reason=item.reason,
                explanation=explanations[item.reason],
                authority=item.guidance.authority,
                revision=item.guidance.revision,
                checks=item.guidance.checks,
            )
            for item in route.items
        )
        required_checks = []
        for item in items:
            for check in item.checks:
                if check not in required_checks:
                    required_checks.append(check)
        omissions = (
            (
                ContextOmission(
                    code="optional-budget-exhausted",
                    guidance_ids=route.omitted_optional_ids,
                    message="Supplemental guidance was omitted because the workspace-context budget was exhausted.",
                ),
            )
            if route.omitted_optional_ids
            else ()
        )
        coverage_status = "partial" if diagnostics or omissions else "complete"
        return ContextReceipt(
            authority=authority,
            items=items,
            required_checks=tuple(required_checks),
            budget=ContextBudget(
                used_optional_characters=route.used_optional_characters,
                optional_character_limit=route.optional_character_limit,
            ),
            coverage=ContextCoverage(
                status=coverage_status,
                selected_count=len(items),
                omitted_count=len(route.omitted_optional_ids),
                diagnostic_count=len(diagnostics),
            ),
            omissions=omissions,
            diagnostics=diagnostics,
            stop_condition=(
                "selected-guidance-and-checks"
                if readiness == "ready" and coverage_status == "complete"
                else "resolve-context-gaps"
            ),
        )
