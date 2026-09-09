import hashlib
import json
import mimetypes
from dataclasses import dataclass
from typing import ClassVar

from wireup import injectable

from ...errors import RecordsError
from ...models import Category, CategorySchemaRevision, Record
from ..categories.service import CategoryService
from ..records.service import RecordService
from .model import (
    CategorySchemaRevisionReceipt,
    RecordCategory,
    RecordCategoryContentSchema,
    RecordCategoryDetail,
    RecordDetail,
    RecordResourceContent,
    RecordTag,
    ResourceManifest,
)


@injectable
@dataclass(frozen=True)
class RecordContentService:
    records: RecordService
    categories: CategoryService

    MAX_CONTENT_CHARACTERS: ClassVar[int] = 512

    def record_detail(self, record: Record) -> RecordDetail:
        return RecordDetail(
            id=record.id,
            title=record.title,
            category=RecordCategory(
                id=record.category.id,
                title=record.category.title,
                schema_version=record.category.schema_version,
            ),
            schema_version=record.schema_version,
            tags=tuple(RecordTag(id=tag.id, name=tag.name) for tag in record.tags.all()),
            content=record.content,
            resources=tuple(
                ResourceManifest(
                    path=resource.path,
                    language=resource.language,
                    media_type=self.media_type(resource.path),
                    size_bytes=len(resource.content.encode("utf-8")),
                    revision=self._revision(resource.content),
                )
                for resource in record.resources.all()
            ),
        )

    def category_detail(self, category: Category) -> RecordCategoryDetail:
        content = self.canonical_schema(category.id, category.schema_version)
        return RecordCategoryDetail(
            id=category.id,
            title=category.title,
            schema_version=category.schema_version,
            content_schema_revision=self._revision(content),
            content_schema_size_bytes=len(content.encode("utf-8")),
        )

    def category_schema_receipt(self, schema: CategorySchemaRevision) -> CategorySchemaRevisionReceipt:
        content = self.canonical_schema(schema.category_id, schema.version)
        return CategorySchemaRevisionReceipt(
            category_id=schema.category_id,
            version=schema.version,
            revision=self._revision(content),
            size_bytes=len(content.encode("utf-8")),
        )

    def read_record_resource(
        self,
        record_id: str,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordResourceContent:
        resource = self.records.get_resource(record_id, path)
        revision = self._revision(resource.content)
        self._require_revision(revision, expected_revision)
        next_offset = self._next_offset(resource.content, offset, limit)
        return RecordResourceContent(
            record_id=record_id,
            path=resource.path,
            language=resource.language,
            media_type=self.media_type(resource.path),
            revision=revision,
            offset=offset,
            limit=limit,
            total_characters=len(resource.content),
            content=resource.content[offset:next_offset],
            has_more=next_offset < len(resource.content),
            next_offset=next_offset,
        )

    def read_record_category_content_schema(
        self,
        category_id: str,
        schema_version: int,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordCategoryContentSchema:
        schema = self.canonical_schema(category_id, schema_version)
        revision = self._revision(schema)
        self._require_revision(revision, expected_revision)
        next_offset = self._next_offset(schema, offset, limit)
        return RecordCategoryContentSchema(
            category_id=category_id,
            schema_version=schema_version,
            revision=revision,
            offset=offset,
            limit=limit,
            total_characters=len(schema),
            content=schema[offset:next_offset],
            has_more=next_offset < len(schema),
            next_offset=next_offset,
        )

    def resource_revision(self, record_id: str, path: str) -> str:
        return self._revision(self.records.get_resource(record_id, path).content)

    def category_schema_revision(self, category_id: str, schema_version: int) -> str:
        return self._revision(self.canonical_schema(category_id, schema_version))

    def canonical_schema(self, category_id: str, schema_version: int) -> str:
        revision = self.categories.get_revision(category_id, schema_version)
        return json.dumps(
            revision.content_schema,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def media_type(self, path: str) -> str:
        return mimetypes.guess_type(path, strict=False)[0] or "text/plain"

    def _revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _require_revision(self, revision: str, expected_revision: str) -> None:
        if revision != expected_revision:
            raise RecordsError("Record content changed; get its manifest again before reading content.")

    def _next_offset(self, content: str, offset: int, limit: int) -> int:
        if limit < 1 or limit > self.MAX_CONTENT_CHARACTERS:
            raise RecordsError(f"Record content limit must be between 1 and {self.MAX_CONTENT_CHARACTERS}.")
        if offset < 0 or offset > len(content):
            raise RecordsError("Record content offset is outside the document.")
        return min(offset + limit, len(content))
