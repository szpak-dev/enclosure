from pydantic import BaseModel, ConfigDict, JsonValue

from ...models import Scaffolding
from ..spec.template import WriteMode


class TemplateManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    write_mode: WriteMode
    size_bytes: int
    revision: str


class ScaffoldingSpecManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    variables: tuple[dict[str, JsonValue], ...]
    templates: tuple[TemplateManifest, ...]


class ScaffoldingDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    language_id: str
    name: str
    description: str
    spec: ScaffoldingSpecManifest


class ScaffoldingTemplateContent(BaseModel):
    model_config = ConfigDict(frozen=True)

    scaffolding_id: str
    path: str
    write_mode: WriteMode
    revision: str
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int


class ScaffoldingPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: tuple[Scaffolding, ...]
    has_more: bool
    next_offset: int
    limit: int
