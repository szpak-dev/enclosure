from dataclasses import dataclass

from django.db import transaction
from django.db.models import QuerySet
from pydantic import JsonValue
from wireup import injectable

from ..models import Category, CategorySchemaRevision, Record, Tag
from .categories.service import CategoryService
from .content import (
    CategoryPage,
    CategorySchemaRevisionReceipt,
    RecordCategoryContentSchema,
    RecordCategoryDetail,
    RecordContentService,
    RecordDetail,
    RecordJsonContent,
    RecordPage,
    RecordResourceContent,
    ResourceManifestPage,
    TagPage,
)
from .records.model import RecordInput
from .records.service import RecordService
from .tags.service import TagService


@injectable
@dataclass(frozen=True)
class RecordsService:
    categories: CategoryService
    tags: TagService
    records: RecordService
    content: RecordContentService

    def create_category(self, title: str, content_schema: dict[str, JsonValue]) -> Category:
        return self.categories.create(title, content_schema)

    def create_category_detail(self, title: str, content_schema: dict[str, JsonValue]) -> RecordCategoryDetail:
        return self.content.category_detail(self.create_category(title, content_schema))

    def get_category(self, id: str) -> Category:
        return self.categories.get(id)

    def get_category_detail(self, id: str) -> RecordCategoryDetail:
        return self.content.category_detail(self.get_category(id))

    def find_all_categories(self, offset: int, limit: int) -> QuerySet[Category]:
        return self.categories.find_all(offset, limit)

    def find_category_page(self, offset: int, limit: int) -> CategoryPage:
        categories = tuple(self.find_all_categories(offset, limit))
        items = categories[:limit]
        return CategoryPage(
            items=items,
            has_more=len(categories) > limit,
            next_offset=offset + len(items),
            limit=limit,
        )

    def update_category(self, id: str, title: str) -> Category:
        return self.categories.update(id, title)

    def update_category_detail(
        self,
        id: str,
        title: str,
    ) -> RecordCategoryDetail:
        return self.content.category_detail(self.update_category(id, title))

    def update_category_content_schema(
        self,
        id: str,
        content_schema: dict[str, JsonValue],
    ) -> CategorySchemaRevision:
        return self.categories.update_content_schema(id, content_schema)

    def update_category_content_schema_receipt(
        self,
        id: str,
        content_schema: dict[str, JsonValue],
    ) -> CategorySchemaRevisionReceipt:
        return self.content.category_schema_receipt(self.update_category_content_schema(id, content_schema))

    def delete_category(self, id: str) -> None:
        self.categories.delete(id)

    def create_tag(self, name: str) -> Tag:
        return self.tags.create(name)

    def get_tag(self, id: str) -> Tag:
        return self.tags.get(id)

    def find_all_tags(self, offset: int, limit: int) -> QuerySet[Tag]:
        return self.tags.find_all(offset, limit)

    def find_tag_page(self, offset: int, limit: int) -> TagPage:
        tags = tuple(self.find_all_tags(offset, limit))
        items = tags[:limit]
        return TagPage(
            items=items,
            has_more=len(tags) > limit,
            next_offset=offset + len(items),
            limit=limit,
        )

    def update_tag(self, id: str, name: str) -> Tag:
        return self.tags.update(id, name)

    def delete_tag(self, id: str) -> None:
        self.tags.delete(id)

    @transaction.atomic
    def create_record(self, data: RecordInput) -> Record:
        schema_version = self.categories.current_schema_version(data.category_id)
        self.categories.validate_content(data.category_id, schema_version, data.content)
        self.tags.require_all(data.tag_ids)
        return self.records.create(data, schema_version)

    def create_record_detail(self, data: RecordInput) -> RecordDetail:
        return self.content.record_detail(self.create_record(data))

    def get_record(self, id: str) -> Record:
        return self.records.get(id)

    def get_record_detail(self, id: str) -> RecordDetail:
        return self.content.record_detail(self.get_record(id))

    def find_all_records(self, offset: int, limit: int) -> QuerySet[Record]:
        return self.records.find_all(offset, limit)

    def find_record_page(self, offset: int, limit: int) -> RecordPage:
        records = tuple(self.find_all_records(offset, limit))
        items = records[:limit]
        return RecordPage(
            items=items,
            has_more=len(records) > limit,
            next_offset=offset + len(items),
            limit=limit,
        )

    def search_records(
        self,
        query: str,
        limit: int = 10,
        record_ids: tuple[str, ...] | None = None,
    ) -> list[Record]:
        return self.records.search(query, limit, record_ids)

    @transaction.atomic
    def update_record(self, id: str, data: RecordInput) -> Record:
        current_schema_version = self.categories.current_schema_version(data.category_id)
        schema_version = self.records.schema_version(
            id,
            data.category_id,
            current_schema_version,
        )
        self.categories.validate_content(data.category_id, schema_version, data.content)
        self.tags.require_all(data.tag_ids)
        return self.records.update(id, data, schema_version)

    def update_record_detail(self, id: str, data: RecordInput) -> RecordDetail:
        return self.content.record_detail(self.update_record(id, data))

    def delete_record(self, id: str) -> None:
        self.records.delete(id)

    def read_record_resource(
        self,
        record_id: str,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordResourceContent:
        return self.content.read_record_resource(record_id, path, expected_revision, offset, limit)

    def read_record_content(
        self,
        record_id: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordJsonContent:
        return self.content.read_record_content(record_id, expected_revision, offset, limit)

    def read_record_resource_manifests(
        self,
        record_id: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ResourceManifestPage:
        return self.content.read_record_resource_manifests(record_id, expected_revision, offset, limit)

    def read_record_category_content_schema(
        self,
        category_id: str,
        schema_version: int,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordCategoryContentSchema:
        return self.content.read_record_category_content_schema(
            category_id,
            schema_version,
            expected_revision,
            offset,
            limit,
        )
