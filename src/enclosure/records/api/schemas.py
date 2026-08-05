from typing import Annotated

from ninja import Schema
from pydantic import Field, JsonValue

CategoryId = Annotated[str, Field(description="Record category identifier.")]
RecordId = Annotated[str, Field(description="Record identifier.")]
TagId = Annotated[str, Field(description="Record tag identifier.")]


class CategoryInput(Schema):
    title: str = Field(description="Unique category title.")
    content_schema: dict[str, JsonValue] = Field(
        description="JSON Schema Draft 2020-12 used to validate record content."
    )


class Category(Schema):
    id: CategoryId
    title: str = Field(description="Unique category title.")
    content_schema: dict[str, JsonValue] = Field(description="JSON Schema used to validate record content.")


class TagInput(Schema):
    name: str = Field(description="Unique tag name.")


class Tag(Schema):
    id: TagId
    name: str = Field(description="Unique tag name.")


class ResourceInput(Schema):
    path: str = Field(description="Relative path identifying the source resource.")
    language: str = Field(description="Language identifier used to interpret the source resource.")
    content: str = Field(description="Complete source text of the resource.")


class Resource(Schema):
    path: str = Field(description="Relative path identifying the source resource.")
    language: str = Field(description="Language identifier used to interpret the source resource.")
    content: str = Field(description="Complete source text of the resource.")


class RecordInput(Schema):
    title: str = Field(description="Human-readable record title.")
    content: dict[str, JsonValue] = Field(description="Content validated against the selected category's schema.")
    category_id: CategoryId = Field(description="Identifier of the category whose schema validates the content.")
    tag_ids: list[TagId] = Field(description="Identifiers of tags assigned to the record.", min_length=1)
    resources: list[ResourceInput] = Field(
        default_factory=list,
        description="Source resources attached to the record.",
    )


class RecordSummary(Schema):
    id: RecordId
    title: str = Field(description="Human-readable record title.")
    category: Category = Field(description="Category that defines the record's content schema.")
    tags: list[Tag] = Field(description="Tags assigned to the record.")


class Record(RecordSummary):
    content: dict[str, JsonValue] = Field(description="Content validated against the category's schema.")
    resources: list[Resource] = Field(description="Source resources attached to the record.")


class SearchInput(Schema):
    query: str = Field(
        description="Natural-language query used for semantic similarity search.",
        min_length=1,
        pattern=r"\S",
    )
    limit: int = Field(default=10, description="Maximum number of records to return.", ge=1)
