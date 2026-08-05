from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from enclosure.shared import SourceCodePackage

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

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        try:
            SourceCodePackage.model_validate(
                {"language": "", "package": {"files": {path: ""}}},
            )
        except ValidationError as error:
            raise ScaffoldingError(error.errors()[0]["msg"]) from error
        return path
