from pydantic import BaseModel, ConfigDict, JsonValue

from ...models import Category, Record, Tag


class RecordContentPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: str
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int


class RecordResourceContent(RecordContentPage):
    record_id: str
    path: str
    language: str
    media_type: str


class RecordJsonContent(RecordContentPage):
    record_id: str


class RecordCategoryContentSchema(RecordContentPage):
    category_id: str
    schema_version: int


class ResourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    language: str
    media_type: str
    size_bytes: int
    revision: str


class ResourceManifestPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    revision: str
    offset: int
    limit: int
    total: int
    items: tuple[ResourceManifest, ...]
    has_more: bool
    next_offset: int


class RecordCategory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    schema_version: int


class RecordTag(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str


class RecordDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    category: RecordCategory
    schema_version: int
    tags: tuple[RecordTag, ...]
    content: dict[str, JsonValue]
    content_revision: str
    content_total_characters: int
    resources: tuple[ResourceManifest, ...]
    resources_revision: str
    resource_count: int


class RecordCategoryDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    schema_version: int
    content_schema_revision: str
    content_schema_size_bytes: int


class CategorySchemaRevisionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category_id: str
    version: int
    revision: str
    size_bytes: int


class TagPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[Tag, ...]
    has_more: bool
    next_offset: int
    limit: int


class CategoryPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[Category, ...]
    has_more: bool
    next_offset: int
    limit: int


class RecordPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[Record, ...]
    has_more: bool
    next_offset: int
    limit: int
