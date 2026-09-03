from abc import ABC, abstractmethod

from ..model import GuidanceFinding, GuidanceGraph, GuidanceRule, RemediationCategory


class GuidanceValidator(ABC):
    name: str
    order: int
    blocking: bool

    @abstractmethod
    def check(self, graph: GuidanceGraph) -> tuple[GuidanceFinding, ...]: ...

    def finding(
        self,
        rule: GuidanceRule,
        source_id: str,
        guidance_ids: tuple[str, ...],
        message: str,
        remediation: RemediationCategory,
    ) -> GuidanceFinding:
        return GuidanceFinding(
            rule=rule,
            source_id=source_id,
            guidance_ids=guidance_ids,
            message=message,
            remediation=remediation,
        )
