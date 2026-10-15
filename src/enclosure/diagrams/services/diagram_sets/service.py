from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...models import DiagramOrdering, DiagramSet
from ..repository import DiagramsRepository
from .model import DiagramSetPage, DiagramSetSummary


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

    def find_page(self, offset: int, limit: int, ordering: DiagramOrdering) -> DiagramSetPage:
        diagram_sets = tuple(self.repository.find_set_page(offset, limit, ordering))
        items = tuple(
            DiagramSetSummary(
                id=diagram_set.id,
                title=diagram_set.title,
                description=diagram_set.description,
                created_at=diagram_set.created_at,
                updated_at=diagram_set.diagram_activity_at,
            )
            for diagram_set in diagram_sets[:limit]
        )
        return DiagramSetPage(
            items=items,
            has_more=len(diagram_sets) > limit,
            next_offset=offset + len(items),
            limit=limit,
            order_by=ordering.field,
            direction=ordering.direction,
        )

    def replace(self, id: str, title: str, description: str) -> DiagramSet:
        return self.repository.replace_set(id, title, description)

    def delete(self, id: str) -> None:
        self.repository.delete_set(id)
