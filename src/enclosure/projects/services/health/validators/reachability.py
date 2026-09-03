from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRequirement, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="reachability")
@dataclass(frozen=True)
class ReachabilityValidator(GuidanceValidator):
    name: str = field(default="reachability", init=False)
    order: int = field(default=60, init=False)
    blocking: bool = field(default=False, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        nodes = {node.guidance.id: node for node in graph.nodes}
        adjacency: defaultdict[str, set[str]] = defaultdict(set)
        for relationship in graph.relationships:
            if relationship.source_record_id in nodes and relationship.target_record_id in nodes:
                adjacency[relationship.source_record_id].add(relationship.target_record_id)
        reachable = set()
        pending = [record_id for record_id in graph.entry_point_ids if record_id in nodes]
        while pending:
            current = pending.pop()
            if current in reachable:
                continue
            reachable.add(current)
            pending.extend(sorted(adjacency[current] - reachable, reverse=True))
        return tuple(
            self.finding(
                GuidanceRule.UNREACHABLE_GUIDANCE,
                node.guidance.id,
                (node.guidance.id,),
                "Supplemental guidance is not reachable from an operating-contract entry point.",
                RemediationCategory.REACHABILITY,
            )
            for node in graph.nodes
            if node.requirement == GuidanceRequirement.SUPPLEMENTAL and node.guidance.id not in reachable
        )
