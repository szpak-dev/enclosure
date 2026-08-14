from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from enclosure.shared import DomainError, JsonSchemaService

from ...errors import RecordsError
from ...models import Category, CategorySchemaRevision
from .repository import CategoryRepository


@injectable
@dataclass(frozen=True)
class CategoryService:
    repository: CategoryRepository
    schemas: JsonSchemaService

    def create(self, data: dict) -> Category:
        return self.repository.save(
            title=data["title"],
            content_schema=self._valid_schema(data["content_schema"]),
        )

    def get(self, id: str) -> Category:
        return self.repository.get(id)

    def find_all(self) -> QuerySet[Category]:
        return self.repository.find_all()

    def update(self, id: str, data: dict) -> Category:
        return self.repository.update(id, title=data["title"])

    def update_content_schema(self, id: str, content_schema: dict) -> CategorySchemaRevision:
        return self.repository.update_content_schema(id, self._valid_schema(content_schema))

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def validate_content(self, category_id: str, version: int, content: object) -> None:
        revision = self.repository.get_revision(category_id, version)
        try:
            self.schemas.load(revision.content_schema).require_valid(content)
        except DomainError as error:
            raise RecordsError(str(error)) from error

    def _valid_schema(self, content_schema: dict) -> dict:
        try:
            schema = self.schemas.load(content_schema)
        except DomainError as error:
            raise RecordsError(str(error)) from error
        return schema.document
