from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, JsonValue


class PresentationValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class McpPresentation(PresentationValue):
    markdown: str
    structured_content: Mapping[str, JsonValue]
    is_error: bool
