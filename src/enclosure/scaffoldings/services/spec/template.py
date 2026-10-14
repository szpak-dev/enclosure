from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from enclosure.shared.source_code.errors import SourceCodeError
from enclosure.shared.source_code.package import CodePackage

from ...errors import ScaffoldingError


class WriteMode(StrEnum):
    OVERWRITE = "overwrite"
    CREATE_IF_MISSING = "create_if_missing"


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(description="Relative output path of the rendered file.")
    content: str = Field(description="Template source rendered into the output file.")
    write_mode: WriteMode = Field(
        default=WriteMode.OVERWRITE,
        description="Whether rendering may replace an existing file.",
    )

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        try:
            CodePackage(files={self.path: self.content})
        except SourceCodeError as error:
            raise ScaffoldingError(f"Invalid scaffolding template path {self.path!r}: {error}") from error
        if not self.path.endswith(".jinja") and any(token in self.content for token in ("{{", "{%", "{#")):
            raise ScaffoldingError("Template content uses Jinja syntax; its path must end with '.jinja'.")
        return self
