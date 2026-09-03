from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..model import (
    GuidanceFinding,
    GuidanceGraph,
    GuidanceRelationship,
    GuidanceRelationshipKind,
    GuidanceRule,
    RemediationCategory,
)
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="relationships")
@dataclass(frozen=True)
class RelationshipValidator(GuidanceValidator):
    name: str = field(default="relationships", init=False)
    order: int = field(default=20, init=False)
    blocking: bool = field(default=True, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        nodes = {node.guidance.id for node in graph.nodes}
        findings = []
        pairs: defaultdict[tuple[str, str], list[GuidanceRelationship]] = defaultdict(list)
        containment_parents: defaultdict[str, set[str]] = defaultdict(set)
        for relationship in graph.relationships:
            guidance_ids = (relationship.source_record_id, relationship.target_record_id)
            if relationship.source_record_id not in nodes or relationship.target_record_id not in nodes:
                findings.append(
                    self.finding(
                        GuidanceRule.DANGLING_RELATIONSHIP,
                        relationship.id,
                        guidance_ids,
                        "A relationship endpoint is outside the project's effective guidance graph.",
                        RemediationCategory.RELATIONSHIP,
                    )
                )
                continue
            if relationship.source_record_id == relationship.target_record_id:
                findings.append(
                    self.finding(
                        GuidanceRule.INVALID_RELATIONSHIP,
                        relationship.id,
                        guidance_ids,
                        "A guidance relationship cannot target its own source.",
                        RemediationCategory.RELATIONSHIP,
                    )
                )
            pairs[(relationship.source_record_id, relationship.target_record_id)].append(relationship)
            if relationship.kind == GuidanceRelationshipKind.CONTAINMENT:
                containment_parents[relationship.target_record_id].add(relationship.source_record_id)

        for relationships in pairs.values():
            if len(relationships) > 1:
                findings.append(
                    self.finding(
                        GuidanceRule.INVALID_RELATIONSHIP,
                        relationships[0].id,
                        (relationships[0].source_record_id, relationships[0].target_record_id),
                        "The same guidance pair cannot carry multiple relationship meanings.",
                        RemediationCategory.RELATIONSHIP,
                    )
                )
        for target_id, parent_ids in sorted(containment_parents.items()):
            if len(parent_ids) > 1:
                findings.append(
                    self.finding(
                        GuidanceRule.INVALID_RELATIONSHIP,
                        target_id,
                        (*sorted(parent_ids), target_id),
                        "Contained guidance must have one effective parent.",
                        RemediationCategory.RELATIONSHIP,
                    )
                )
        return tuple(findings)
