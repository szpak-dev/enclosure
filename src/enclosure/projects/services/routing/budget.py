from dataclasses import dataclass

from wireup import injectable

from .model import GuidanceCandidate


@injectable
@dataclass(frozen=True)
class GuidanceBudgetService:
    def select(
        self,
        candidates: tuple[GuidanceCandidate, ...],
        max_characters: int,
    ) -> tuple[GuidanceCandidate, ...]:
        selected = []
        used = 0
        for candidate in candidates:
            characters = len(candidate.guidance.model_dump_json())
            if used + characters > max_characters:
                break
            selected.append(candidate)
            used += characters
        return tuple(selected)
