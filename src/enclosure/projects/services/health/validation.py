from collections.abc import Sequence
from dataclasses import dataclass
from operator import attrgetter

from wireup import injectable

from ..contracts.model import ConfiguredOperatingContractBinding, UnconfiguredOperatingContractBinding
from .graph import GuidanceGraphService
from .model import GuidanceHealthMetadata, GuidanceHealthReport
from .validators.base import GuidanceValidator


@injectable
@dataclass(frozen=True)
class GuidanceHealthService:
    graphs: GuidanceGraphService
    validators: Sequence[GuidanceValidator]

    def check(
        self,
        project_id: str,
        binding: ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding,
    ) -> GuidanceHealthReport:
        graph = self.graphs.build(project_id, binding)
        violations = []
        advisories = []
        for validator in sorted(self.validators, key=attrgetter("order", "name")):
            findings = validator.check(graph)
            if validator.blocking:
                violations.extend(findings)
            else:
                advisories.extend(findings)
        return GuidanceHealthReport(
            healthy=not violations,
            metadata=GuidanceHealthMetadata(
                id="guidance-graph",
                title="Guidance graph",
                description="Project-wide operating guidance integrity.",
                model="GuidanceGraph",
                path=f"projects/{project_id}/guidance",
                order=0,
                children=tuple(sorted(node.guidance.id for node in graph.nodes)),
            ),
            violations=tuple(violations),
            advisories=tuple(advisories),
        )
