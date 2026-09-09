from typing import Annotated

from ninja import Schema
from pydantic import Field, JsonValue

CategoryId = Annotated[str, Field(description="Record category identifier.")]
RecordId = Annotated[str, Field(description="Record identifier.")]
TagId = Annotated[str, Field(description="Record tag identifier.")]


class CreateCategory(Schema):
    title: str = Field(description="Unique category title.")
    content_schema: dict[str, JsonValue] = Field(
        description="JSON Schema Draft 2020-12 used to validate record content."
    )


class UpdateCategory(Schema):
    title: str = Field(description="Unique category title.")


class UpdateCategoryContentSchema(Schema):
    content_schema: dict[str, JsonValue] = Field(
        description="JSON Schema Draft 2020-12 used to validate record content."
    )


class CategorySchemaRevision(Schema):
    category_id: CategoryId
    version: int = Field(description="Category-local content schema version.", ge=1)
    revision: str = Field(description="SHA-256 revision of the canonical JSON Schema document.")
    size_bytes: int = Field(description="Canonical JSON Schema size in bytes.", ge=0)


class Category(Schema):
    id: CategoryId
    title: str = Field(description="Unique category title.")
    schema_version: int = Field(description="Current content schema version.", ge=1)
    content_schema_revision: str = Field(description="SHA-256 revision of the current canonical schema.")
    content_schema_size_bytes: int = Field(description="Current canonical schema size in bytes.", ge=0)


class CategoryReference(Schema):
    id: CategoryId
    title: str = Field(description="Unique category title.")
    schema_version: int = Field(description="Current content schema version.", ge=1)


class RecordCategory(Schema):
    id: CategoryId
    title: str = Field(description="Unique category title.")
    schema_version: int = Field(description="Current content schema version.", ge=1)


class WriteTag(Schema):
    name: str = Field(description="Unique tag name.")


class Tag(Schema):
    id: TagId
    name: str = Field(description="Unique tag name.")


class Resource(Schema):
    path: str = Field(description="Relative path identifying the source resource.")
    language: str = Field(description="Language identifier used to interpret the source resource.")
    content: str = Field(description="Complete source text of the resource.")


class ResourceManifest(Schema):
    path: str = Field(description="Relative path identifying the source resource.")
    language: str = Field(description="Language identifier used to interpret the source resource.")
    media_type: str = Field(description="Media type inferred from the resource path.")
    size_bytes: int = Field(description="Source-resource size in bytes.", ge=0)
    revision: str = Field(description="SHA-256 revision of the complete source text.")


class WriteRecord(Schema):
    title: str = Field(description="Human-readable record title.")
    content: dict[str, JsonValue] = Field(description="Content validated against the selected category's schema.")
    category_id: CategoryId = Field(description="Identifier of the category whose schema validates the content.")
    tag_ids: list[TagId] = Field(description="Identifiers of tags assigned to the record.", min_length=1)
    resources: list[Resource] = Field(
        default_factory=list,
        description="Source resources attached to the record.",
    )


class RecordSummary(Schema):
    id: RecordId
    title: str = Field(description="Human-readable record title.")
    category: RecordCategory = Field(description="Category that defines the record's content schema.")
    schema_version: int = Field(description="Content schema version assigned to the record.", ge=1)
    tags: list[Tag] = Field(description="Tags assigned to the record.")


class Record(RecordSummary):
    content: dict[str, JsonValue] = Field(description="Content validated against the category's schema.")
    resources: list[ResourceManifest] = Field(description="Source-resource manifests without complete bodies.")


class FindPage(Schema):
    offset: int = Field(default=0, description="Item offset at which the page starts.", ge=0)
    limit: int = Field(default=50, description="Maximum items returned by the page.", ge=1, le=100)


class TagPage(Schema):
    items: list[Tag] = Field(description="Record tags in this bounded page.")
    has_more: bool = Field(description="Whether another page of record tags remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)


class CategoryPage(Schema):
    items: list[CategoryReference] = Field(description="Record category references in this bounded page.")
    has_more: bool = Field(description="Whether another page of record categories remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)


class RecordPage(Schema):
    items: list[RecordSummary] = Field(description="Compact record summaries in this bounded page.")
    has_more: bool = Field(description="Whether another page of records remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)


class ReadRecordContent(Schema):
    expected_revision: str = Field(
        description="SHA-256 revision on which the read is based.",
        pattern=r"^[0-9a-f]{64}$",
    )
    offset: int = Field(description="Character offset at which the bounded read starts.", ge=0)
    limit: int = Field(description="Maximum characters returned by the bounded read.", ge=1, le=512)


class ReadRecordResource(ReadRecordContent):
    path: str = Field(description="Exact relative path of the source resource.", min_length=1)


class ReadRecordCategoryContentSchema(ReadRecordContent):
    schema_version: int = Field(description="Category-local schema version to read.", ge=1)


class RecordResourceContent(Schema):
    record_id: RecordId
    path: str = Field(description="Exact relative path of the source resource.")
    language: str = Field(description="Language identifier used to interpret the source resource.")
    media_type: str = Field(description="Media type inferred from the resource path.")
    revision: str = Field(description="SHA-256 revision of the complete source text.")
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1, le=512)
    total_characters: int = Field(description="Total characters in the source resource.", ge=0)
    content: str = Field(description="Bounded source-resource content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)


class RecordCategoryContentSchema(Schema):
    category_id: CategoryId
    schema_version: int = Field(description="Category-local schema version used for this read.", ge=1)
    revision: str = Field(description="SHA-256 revision of the canonical JSON Schema document.")
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1, le=512)
    total_characters: int = Field(description="Total characters in the canonical JSON Schema document.", ge=0)
    content: str = Field(description="Bounded canonical JSON Schema content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)


class SearchRecords(Schema):
    query: str = Field(
        description="Natural-language query used for semantic similarity search.",
        min_length=1,
        pattern=r"\S",
    )
    limit: int = Field(default=10, description="Maximum number of records to return.", ge=1, le=100)
