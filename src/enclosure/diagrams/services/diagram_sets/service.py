from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...errors import DiagramsError
from ...models import DiagramSet
from ..repository import DiagramsRepository
from ..validation import DiagramValidationService


@injectable
@dataclass(frozen=True)
class DiagramSetService:
    repository: DiagramsRepository
    validation: DiagramValidationService

    def create(self, data: Mapping[str, object]) -> DiagramSet:
        return self.repository.create_set(self.validation.diagram_set(data, require_title=True))

    def get(self, id: str) -> DiagramSet:
        try:
            return self.repository.get_set(id)
        except DiagramSet.DoesNotExist as error:
            raise DiagramsError(f"Diagram set {id!r} does not exist.") from error

    def find_all(self) -> QuerySet[DiagramSet]:
        return self.repository.find_all_sets()

    def update(self, id: str, data: Mapping[str, object]) -> DiagramSet:
        self.get(id)
        return self.repository.update_set(id, self.validation.diagram_set(data))

    def delete(self, id: str) -> None:
        self.get(id)
        self.repository.delete_set(id)
