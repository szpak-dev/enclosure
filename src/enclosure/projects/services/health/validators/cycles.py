from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="cycles")
@dataclass(frozen=True)
class CycleValidator(GuidanceValidator):
    name: str = field(default="cycles", init=False)
    order: int = field(default=30, init=False)
    blocking: bool = field(default=True, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        nodes = {node.guidance.id for node in graph.nodes}
        adjacency: defaultdict[str, set[str]] = defaultdict(set)
        relationships = tuple(
            relationship
            for relationship in graph.relationships
            if relationship.source_record_id in nodes and relationship.target_record_id in nodes
        )
        for relationship in relationships:
            adjacency[relationship.source_record_id].add(relationship.target_record_id)
        cyclic_ids = set()
        for relationship in relationships:
            if self._reachable(relationship.target_record_id, relationship.source_record_id, adjacency):
                cyclic_ids.update((relationship.source_record_id, relationship.target_record_id))
        if not cyclic_ids:
            return ()
        guidance_ids = tuple(sorted(cyclic_ids))
        return (
            self.finding(
                GuidanceRule.GUIDANCE_CYCLE,
                guidance_ids[0],
                guidance_ids,
                "The effective guidance graph contains a relationship cycle.",
                RemediationCategory.RELATIONSHIP,
            ),
        )

    def _reachable(self, start_id: str, target_id: str, adjacency: dict[str, set[str]]) -> bool:
        pending = [start_id]
        visited = set()
        while pending:
            current = pending.pop()
            if current == target_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(sorted(adjacency[current] - visited, reverse=True))
        return False
