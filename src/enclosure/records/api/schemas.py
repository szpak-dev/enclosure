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
    version: int = Field(description="Category-local content schema version.", ge=1)
    content_schema: dict[str, JsonValue] = Field(description="Versioned JSON Schema document.")


class Category(Schema):
    id: CategoryId
    title: str = Field(description="Unique category title.")
    content_schema: dict[str, JsonValue] = Field(description="JSON Schema used to validate record content.")
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
    category: Category = Field(description="Category that defines the record's content schema.")
    schema_version: int = Field(description="Content schema version assigned to the record.", ge=1)
    tags: list[Tag] = Field(description="Tags assigned to the record.")


class Record(RecordSummary):
    content: dict[str, JsonValue] = Field(description="Content validated against the category's schema.")
    resources: list[Resource] = Field(description="Source resources attached to the record.")


class SearchRecords(Schema):
    query: str = Field(
        description="Natural-language query used for semantic similarity search.",
        min_length=1,
        pattern=r"\S",
    )
    limit: int = Field(default=10, description="Maximum number of records to return.", ge=1)
