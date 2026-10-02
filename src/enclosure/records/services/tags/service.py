from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...errors import RecordsError
from ...models import Tag
from .repository import TagRepository


@injectable
@dataclass(frozen=True)
class TagService:
    repository: TagRepository

    def create(self, name: str) -> Tag:
        return self.repository.save(name)

    def get(self, id: str) -> Tag:
        return self.repository.get(id)

    def find_all(self, offset: int, limit: int) -> QuerySet[Tag]:
        return self.repository.find_all().order_by("id")[offset : offset + limit + 1]

    def update(self, id: str, name: str) -> Tag:
        return self.repository.update(id, name)

    def delete(self, id: str) -> None:
        if self.repository.is_in_use(id):
            raise RecordsError("A tag assigned to records cannot be deleted.")
        self.repository.delete(id)

    def require_all(self, tag_ids: tuple[str, ...]) -> None:
        for tag_id in tag_ids:
            self.get(tag_id)
