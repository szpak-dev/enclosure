from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="entry-points")
@dataclass(frozen=True)
class EntryPointValidator(GuidanceValidator):
    name: str = field(default="entry-points", init=False)
    order: int = field(default=10, init=False)
    blocking: bool = field(default=True, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        nodes = {node.guidance.id for node in graph.nodes}
        findings = []
        if not graph.entry_point_ids:
            findings.append(
                self.finding(
                    GuidanceRule.MISSING_ENTRY_POINT,
                    graph.project_id,
                    (),
                    "The project has no effective operating-contract guidance entry point.",
                    RemediationCategory.CONTRACT,
                )
            )
        for record_id in graph.entry_point_ids:
            if record_id not in nodes:
                findings.append(
                    self.finding(
                        GuidanceRule.MISSING_ENTRY_POINT,
                        record_id,
                        (record_id,),
                        "An operating-contract guidance entry point cannot be resolved.",
                        RemediationCategory.CONTRACT,
                    )
                )

        incoming = defaultdict(list)
        for relationship in graph.relationships:
            if relationship.source_record_id in nodes and relationship.target_record_id in nodes:
                incoming[relationship.target_record_id].append(relationship.source_record_id)
        for record_id in graph.entry_point_ids:
            predecessors = tuple(sorted(set(incoming[record_id]) - {record_id}))
            if predecessors:
                findings.append(
                    self.finding(
                        GuidanceRule.AMBIGUOUS_ENTRY_POINT,
                        record_id,
                        (*predecessors, record_id),
                        "A declared entry point is also governed by incoming guidance relationships.",
                        RemediationCategory.CONTRACT,
                    )
                )
        return tuple(findings)
