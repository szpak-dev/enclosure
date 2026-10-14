from pydantic import BaseModel, ConfigDict

from ..model import ScaffoldingValue
from ..spec.template import WriteMode
from ..spec.variables import Variable


class TemplateManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    write_mode: WriteMode
    size_bytes: int
    revision: str


class ScaffoldingSpecManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    variables: tuple[Variable, ...]
    templates: tuple[TemplateManifest, ...]


class ScaffoldingDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    language_id: str
    name: str
    description: str
    spec: ScaffoldingSpecManifest
    templates_revision: str
    template_count: int


class TemplateManifestPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    scaffolding_id: str
    revision: str
    offset: int
    limit: int
    total: int
    items: tuple[TemplateManifest, ...]
    has_more: bool
    next_offset: int


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
    model_config = ConfigDict(frozen=True)

    items: tuple[ScaffoldingValue, ...]
    has_more: bool
    next_offset: int
    limit: int
