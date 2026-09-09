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

    def create(self, data: dict) -> Tag:
        return self.repository.save(**data)

    def get(self, id: str) -> Tag:
        return self.repository.get(id)

    def find_all(self, offset: int, limit: int) -> QuerySet[Tag]:
        return self.repository.find_all().order_by("id")[offset : offset + limit + 1]

    def update(self, id: str, data: dict) -> Tag:
        return self.repository.update(id, **data)

    def delete(self, id: str) -> None:
        if self.repository.is_in_use(id):
            raise RecordsError("A tag assigned to records cannot be deleted.")
        self.repository.delete(id)

    def require_all(self, tag_ids: list[str]) -> None:
        if not tag_ids:
            raise RecordsError("A record must have at least one tag.")
        if len(tag_ids) != len(set(tag_ids)):
            raise RecordsError("A record cannot contain the same tag more than once.")
        for tag_id in tag_ids:
            self.get(tag_id)
