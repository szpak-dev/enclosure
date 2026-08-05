from dataclasses import dataclass

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ..models import Category, CategorySchemaRevision, Record, Tag
from .categories.service import CategoryService
from .records.service import RecordService
from .tags.service import TagService


@injectable
@dataclass(frozen=True)
class RecordsService:
    categories: CategoryService
    tags: TagService
    records: RecordService

    def create_category(self, data: dict) -> Category:
        return self.categories.create(data)

    def get_category(self, id: str) -> Category:
        return self.categories.get(id)

    def find_all_categories(self) -> QuerySet[Category]:
        return self.categories.find_all()

    def update_category(self, id: str, data: dict) -> Category:
        return self.categories.update(id, data)

    def update_category_content_schema(self, id: str, content_schema: dict) -> CategorySchemaRevision:
        return self.categories.update_content_schema(id, content_schema)

    def delete_category(self, id: str) -> None:
        self.categories.delete(id)

    def create_tag(self, data: dict) -> Tag:
        return self.tags.create(data)

    def get_tag(self, id: str) -> Tag:
        return self.tags.get(id)

    def find_all_tags(self) -> QuerySet[Tag]:
        return self.tags.find_all()

    def update_tag(self, id: str, data: dict) -> Tag:
        return self.tags.update(id, data)

    def delete_tag(self, id: str) -> None:
        self.tags.delete(id)

    @transaction.atomic
    def create_record(self, data: dict) -> Record:
        return self.records.create(self._validated_record(data))

    def get_record(self, id: str) -> Record:
        return self.records.get(id)

    def find_all_records(self) -> QuerySet[Record]:
        return self.records.find_all()

    def search_records(self, query: str, limit: int = 10) -> list[Record]:
        return self.records.search(query, limit)

    @transaction.atomic
    def update_record(self, id: str, data: dict) -> Record:
        existing = self.records.get(id)
        return self.records.update(id, self._validated_record(data, existing))

    def delete_record(self, id: str) -> None:
        self.records.delete(id)

    def _validated_record(self, data: dict, existing: Record | None = None) -> dict:
        category_id = data.get("category_id", existing.category_id if existing else None)
        content = data.get("content", existing.content if existing else None)
        tag_ids = data.get("tag_ids", [tag.id for tag in existing.tags.all()] if existing else None)
        category = Category.objects.select_for_update().get(pk=category_id)
        if existing is not None and category_id == existing.category_id:
            schema_version = existing.schema_version
        else:
            schema_version = category.schema_version
        self.categories.validate_content(category_id, schema_version, content)
        self.tags.require_all(tag_ids)
        return {**data, "schema_version": schema_version}
