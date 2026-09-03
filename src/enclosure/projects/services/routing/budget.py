from dataclasses import dataclass

from wireup import injectable

from .model import GuidanceBudget, GuidanceCandidate


@injectable
@dataclass(frozen=True)
class GuidanceBudgetService:
    def select(
        self,
        candidates: tuple[GuidanceCandidate, ...],
        max_characters: int,
    ) -> GuidanceBudget:
        selected = []
        used = 0
        for candidate in candidates:
            characters = len(candidate.guidance.model_dump_json())
            if used + characters > max_characters:
                break
            selected.append(candidate)
            used += characters
        selected_ids = {candidate.guidance.id for candidate in selected}
        return GuidanceBudget(
            selected=tuple(selected),
            omitted_ids=tuple(
                candidate.guidance.id for candidate in candidates if candidate.guidance.id not in selected_ids
            ),
            used_characters=used,
            limit_characters=max_characters,
        )
