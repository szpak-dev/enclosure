from dataclasses import dataclass

from wireup import injectable

from ..adapters.model import GuidanceRanking
from .model import GuidanceCandidate


@injectable
@dataclass(frozen=True)
class GuidanceOrderingService:
    def order(
        self,
        candidates: tuple[GuidanceCandidate, ...],
        ranking: GuidanceRanking,
    ) -> tuple[GuidanceCandidate, ...]:
        ranked_positions = {record_id: position for position, record_id in enumerate(ranking.ordered_ids)}
        if not ranking.available:
            return tuple(sorted(candidates, key=self._fallback_key))
        return tuple(
            candidate
            for _, candidate in sorted(
                (self._ranking_key(candidate, ranked_positions), candidate) for candidate in candidates
            )
        )

    def _ranking_key(
        self,
        candidate: GuidanceCandidate,
        ranked_positions: dict[str, int],
    ) -> tuple[int, int, str]:
        ranked_position = ranked_positions.get(candidate.guidance.id)
        if ranked_position is not None:
            return 0, ranked_position, candidate.guidance.id
        return 1, candidate.position, candidate.guidance.id

    def _fallback_key(self, candidate: GuidanceCandidate) -> tuple[int, str]:
        return candidate.position, candidate.guidance.id
