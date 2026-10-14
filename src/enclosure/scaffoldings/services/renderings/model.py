from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from enclosure.shared.source_code.errors import SourceCodeError
from enclosure.shared.source_code.package import CodePackage

from ...errors import ScaffoldingError


class RenderedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    content: str
    overwrite: bool

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        try:
            CodePackage(files={self.path: self.content})
        except SourceCodeError as error:
            raise ScaffoldingError(f"Invalid rendered scaffolding path {self.path!r}: {error}") from error
        return self


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
