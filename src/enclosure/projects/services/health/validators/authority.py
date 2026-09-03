from collections import defaultdict
from dataclasses import dataclass, field

from wireup import injectable

from ..model import GuidanceFinding, GuidanceGraph, GuidanceNode, GuidanceRule, RemediationCategory
from .base import GuidanceValidator


@injectable(as_type=GuidanceValidator, qualifier="authority")
@dataclass(frozen=True)
class AuthorityValidator(GuidanceValidator):
    name: str = field(default="authority", init=False)
    order: int = field(default=50, init=False)
    blocking: bool = field(default=True, init=False)

    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]:
        return (*self._authority_findings(graph.nodes), *self._duplicate_policy_findings(graph.nodes))

    def _authority_findings(self, nodes: tuple[GuidanceNode, ...]) -> tuple[GuidanceFinding, ...]:
        authorities: defaultdict[str, list[str]] = defaultdict(list)
        for node in nodes:
            authorities[node.guidance.authority].append(node.guidance.id)
        return tuple(
            self.finding(
                GuidanceRule.AUTHORITY_CONFLICT,
                authority,
                tuple(sorted(guidance_ids)),
                f"Multiple bound guidance records claim authority {authority!r}. Bind one effective source.",
                RemediationCategory.AUTHORITY,
            )
            for authority, guidance_ids in sorted(authorities.items())
            if len(guidance_ids) > 1
        )

    def _duplicate_policy_findings(self, nodes: tuple[GuidanceNode, ...]) -> tuple[GuidanceFinding, ...]:
        policies: defaultdict[tuple[tuple[str, ...], ...], list[GuidanceNode]] = defaultdict(list)
        for node in nodes:
            signature = (node.guidance.applies_when, node.guidance.guidance, node.guidance.checks)
            if any(signature):
                policies[signature].append(node)
        findings = []
        for duplicates in policies.values():
            authorities = {node.guidance.authority for node in duplicates}
            if len(duplicates) < 2 or len(authorities) < 2:
                continue
            guidance_ids = tuple(sorted(node.guidance.id for node in duplicates))
            findings.append(
                self.finding(
                    GuidanceRule.DUPLICATE_EFFECTIVE_POLICY,
                    guidance_ids[0],
                    guidance_ids,
                    "Equivalent effective policy content is declared by multiple authorities.",
                    RemediationCategory.AUTHORITY,
                )
            )
        return tuple(findings)
