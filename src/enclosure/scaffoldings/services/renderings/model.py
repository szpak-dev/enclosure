from pydantic import BaseModel, ConfigDict, field_validator

from enclosure.shared import CodePackage


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
