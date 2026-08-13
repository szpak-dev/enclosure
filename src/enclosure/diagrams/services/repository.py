from dataclasses import dataclass

from wireup import injectable


@injectable
@dataclass(frozen=True)
class DiagramsRepository:
    def status(self) -> str:
        return "ready"
