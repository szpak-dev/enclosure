from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRequirement, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="optional-budget")
@dataclass(frozen=True)
class OptionalBudgetValidator(GuidanceValidator):
    name: str = field(default="optional-budget", init=False)
    order: int = field(default=80, init=False)
    blocking: bool = field(default=False, init=False)
    max_characters: int = field(default=4096, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        optional = tuple(node for node in graph.nodes if node.requirement == GuidanceRequirement.SUPPLEMENTAL)
        used = sum(len(node.guidance.model_dump_json()) for node in optional)
        if used <= self.max_characters:
            return ()
        guidance_ids = tuple(node.guidance.id for node in optional)
        return (
            self.finding(
                GuidanceRule.OPTIONAL_BUDGET_EXCEEDED,
                graph.project_id,
                guidance_ids,
                f"Supplemental guidance uses {used} characters; the project limit is {self.max_characters}.",
                RemediationCategory.BUDGET,
            ),
        )
