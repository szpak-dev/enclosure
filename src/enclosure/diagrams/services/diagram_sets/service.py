from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...models import DiagramSet
from ..repository import DiagramsRepository
from .model import DiagramSetPage


@injectable
@dataclass(frozen=True)
class DiagramSetService:
    repository: DiagramsRepository

    def create(self, title: str, description: str) -> DiagramSet:
        return self.repository.create_set(title, description)

    def get(self, id: str) -> DiagramSet:
        return self.repository.get_set(id)

    def find_all(self) -> QuerySet[DiagramSet]:
        return self.repository.find_all_sets()

    def find_page(self, offset: int, limit: int) -> DiagramSetPage:
        diagram_sets = tuple(self.repository.find_set_page(offset, limit))
        items = diagram_sets[:limit]
        return DiagramSetPage(
            items=items,
            has_more=len(diagram_sets) > limit,
            next_offset=offset + len(items),
            limit=limit,
        )

    def replace(self, id: str, title: str, description: str) -> DiagramSet:
        return self.repository.replace_set(id, title, description)

    def delete(self, id: str) -> None:
        self.repository.delete_set(id)
