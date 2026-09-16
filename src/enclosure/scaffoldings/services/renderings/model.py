from pydantic import BaseModel, ConfigDict, field_validator

from enclosure.shared.source_code.package import CodePackage


class RenderedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    content: str
    overwrite: bool

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        CodePackage(files={path: ""})
        return path


class RenderedFileManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    overwrite: bool
    size_bytes: int
    revision: str
    preview: str


class RenderingPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scaffolding_id: str
    items: tuple[RenderedFileManifest, ...]
    has_more: bool
    next_offset: int
    limit: int


class RenderedFileContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scaffolding_id: str
    path: str
    overwrite: bool
    revision: str
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int
