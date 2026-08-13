from dataclasses import dataclass

from wireup import injectable

from ..repository import DiagramsRepository


@injectable
@dataclass(frozen=True)
class StatusService:
    repository: DiagramsRepository

    def get(self) -> str:
        return self.repository.status()
