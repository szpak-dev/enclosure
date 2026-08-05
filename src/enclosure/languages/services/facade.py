from dataclasses import dataclass

from wireup import injectable

from .status import StatusService


@injectable
@dataclass(frozen=True)
class LanguagesService:
    status_service: StatusService

    def get_status(self) -> str:
        return self.status_service.get()
