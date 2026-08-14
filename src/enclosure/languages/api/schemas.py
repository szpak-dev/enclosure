from ninja import Schema
from pydantic import Field


class Language(Schema):
    id: str = Field(description="Stable language identifier.")
    name: str = Field(description="Human-readable language name.")
    aliases: list[str] = Field(description="Alternative language identifiers.")
    source_extensions: list[str] = Field(description="Recognized source-file extensions.")
