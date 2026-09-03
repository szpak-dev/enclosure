import re
from dataclasses import dataclass

from wireup import injectable

from .model import GuidanceCandidate


@injectable
@dataclass(frozen=True)
class GuidanceApplicabilityService:
    def filter(
        self,
        task: str,
        candidates: tuple[GuidanceCandidate, ...],
    ) -> tuple[GuidanceCandidate, ...]:
        task_tokens = self._tokens(task)
        return tuple(candidate for candidate in candidates if self._applies(candidate, task_tokens))

    def _applies(self, candidate: GuidanceCandidate, task_tokens: frozenset[str]) -> bool:
        selectors = candidate.guidance.applies_when
        if not selectors:
            return True
        return any(
            selector_tokens <= task_tokens for selector in selectors if (selector_tokens := self._tokens(selector))
        )

    def _tokens(self, value: str) -> frozenset[str]:
        return frozenset(token.casefold() for token in re.findall(r"\w+", value))
