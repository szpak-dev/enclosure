from dataclasses import dataclass

from wireup import injectable


@injectable
@dataclass(frozen=True)
class DiagramsService:
    pass
