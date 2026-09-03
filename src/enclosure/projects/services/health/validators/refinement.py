from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    GuidanceFinding,
    GuidanceGraph,
    GuidanceRelationshipKind,
    GuidanceRule,
    RemediationCategory,
)
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="refinement")
@dataclass(frozen=True)
class RefinementValidator(GuidanceValidator):
    name: str = field(default="refinement", init=False)
    order: int = field(default=40, init=False)
    blocking: bool = field(default=True, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        nodes = {node.guidance.id: node for node in graph.nodes}
        findings = []
        for relationship in graph.relationships:
            source = nodes.get(relationship.source_record_id)
            target = nodes.get(relationship.target_record_id)
            if source is None or target is None:
                continue
            if relationship.kind == GuidanceRelationshipKind.REFINEMENT and not target.guidance.authority.startswith(
                f"{source.guidance.authority}:"
            ):
                findings.append(
                    self.finding(
                        GuidanceRule.INVALID_REFINEMENT,
                        relationship.id,
                        (source.guidance.id, target.guidance.id),
                        "Refined guidance must declare an authority beneath the source authority.",
                        RemediationCategory.AUTHORITY,
                    )
                )
            if relationship.kind == GuidanceRelationshipKind.ESCALATION and not source.guidance.authority.startswith(
                f"{target.guidance.authority}:"
            ):
                findings.append(
                    self.finding(
                        GuidanceRule.INVALID_RELATIONSHIP,
                        relationship.id,
                        (source.guidance.id, target.guidance.id),
                        "Escalated guidance must target a parent authority.",
                        RemediationCategory.AUTHORITY,
                    )
                )
        return tuple(findings)
