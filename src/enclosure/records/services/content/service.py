import hashlib
import json
import mimetypes
from dataclasses import dataclass

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
    RecordJsonContent,
    RecordResourceContent,
    RecordTag,
    ResourceManifest,
    ResourceManifestPage,
)


@injectable
@dataclass(frozen=True)
class RecordContentService:
    records: RecordService
    categories: CategoryService

    def record_detail(self, record: Record) -> RecordDetail:
        content = self._canonical_json(record.content)
        resources = self._resource_manifests(record)
        resources_document = self._canonical_json([item.model_dump(mode="json") for item in resources])
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
            content_revision=self._revision(content),
            content_total_characters=len(content),
            resources=resources,
            resources_revision=self._revision(resources_document),
            resource_count=len(resources),
        )

    def read_record_content(
        self,
        record_id: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RecordJsonContent:
        content = self._canonical_json(self.records.get(record_id).content)
        revision = self._revision(content)
        self._require_revision(revision, expected_revision)
        effective_limit = self._effective_limit(len(content), offset, limit)
        next_offset = self._next_offset(content, offset, effective_limit)
        return RecordJsonContent(
            record_id=record_id,
            revision=revision,
            offset=offset,
            limit=effective_limit,
            total_characters=len(content),
            content=content[offset:next_offset],
            has_more=next_offset < len(content),
            next_offset=next_offset,
        )

    def read_record_resource_manifests(
        self,
        record_id: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ResourceManifestPage:
        manifests = self._resource_manifests(self.records.get(record_id))
        document = self._canonical_json([item.model_dump(mode="json") for item in manifests])
        revision = self._revision(document)
        self._require_revision(revision, expected_revision)
        if offset > len(manifests):
            raise RecordsError("Record resource-manifest offset is outside the collection.")
        effective_limit = self._effective_limit(len(manifests), offset, limit)
        items = manifests[offset : offset + effective_limit]
        next_offset = offset + len(items)
        return ResourceManifestPage(
            record_id=record_id,
            revision=revision,
            offset=offset,
            limit=effective_limit,
            total=len(manifests),
            items=items,
            has_more=next_offset < len(manifests),
            next_offset=next_offset,
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
        effective_limit = self._effective_limit(len(resource.content), offset, limit)
        next_offset = self._next_offset(resource.content, offset, effective_limit)
        return RecordResourceContent(
            record_id=record_id,
            path=resource.path,
            language=resource.language,
            media_type=self.media_type(resource.path),
            revision=revision,
            offset=offset,
            limit=effective_limit,
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
        effective_limit = self._effective_limit(len(schema), offset, limit)
        next_offset = self._next_offset(schema, offset, effective_limit)
        return RecordCategoryContentSchema(
            category_id=category_id,
            schema_version=schema_version,
            revision=revision,
            offset=offset,
            limit=effective_limit,
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
        return self._canonical_json(revision.content_schema)

    def media_type(self, path: str) -> str:
        return mimetypes.guess_type(path, strict=False)[0] or "text/plain"

    def _revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _canonical_json(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def _resource_manifests(self, record: Record) -> tuple[ResourceManifest, ...]:
        return tuple(
            ResourceManifest(
                path=resource.path,
                language=resource.language,
                media_type=self.media_type(resource.path),
                size_bytes=len(resource.content.encode("utf-8")),
                revision=self._revision(resource.content),
            )
            for resource in sorted(record.resources.all(), key=lambda item: item.path)
        )

    def _effective_limit(self, total: int, offset: int, limit: int) -> int:
        return max(1, total - offset) if limit == 0 else limit

    def _require_revision(self, revision: str, expected_revision: str) -> None:
        if revision != expected_revision:
            raise RecordsError("Record content changed; get its manifest again before reading content.")

    def _next_offset(self, content: str, offset: int, limit: int) -> int:
        if offset > len(content):
            raise RecordsError("Record content offset is outside the document.")
        return min(offset + limit, len(content))
