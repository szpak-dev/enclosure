from dataclasses import dataclass

from wireup import injectable


@injectable
@dataclass(frozen=True)
class LanguagesRepository:
    def status(self) -> str:
        return "ready"
