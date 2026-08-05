from dataclasses import dataclass

from wireup import injectable

from ..repository import LanguagesRepository


@injectable
@dataclass(frozen=True)
class StatusService:
    repository: LanguagesRepository

    def get(self) -> str:
        return self.repository.status()
