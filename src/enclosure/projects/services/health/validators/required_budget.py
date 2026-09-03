from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRequirement, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="required-budget")
@dataclass(frozen=True)
class RequiredBudgetValidator(GuidanceValidator):
    name: str = field(default="required-budget", init=False)
    order: int = field(default=70, init=False)
    blocking: bool = field(default=True, init=False)
    max_characters: int = field(default=8192, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        required = tuple(node for node in graph.nodes if node.requirement == GuidanceRequirement.MANDATORY)
        used = sum(len(node.guidance.model_dump_json()) for node in required)
        if used <= self.max_characters:
            return ()
        guidance_ids = tuple(node.guidance.id for node in required)
        return (
            self.finding(
                GuidanceRule.GUIDANCE_OVERSIZED,
                graph.project_id,
                guidance_ids,
                f"Required guidance uses {used} characters; the project limit is {self.max_characters}.",
                RemediationCategory.BUDGET,
            ),
        )
