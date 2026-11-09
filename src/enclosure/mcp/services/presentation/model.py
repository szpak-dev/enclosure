from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ..operations import ToolInvocation


class PresentationValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    INCOMPLETE = "incomplete"


class PresentationImage(PresentationValue):
    data: str
    media_type: str


class PresentationEnvelope(PresentationValue):
    operation_id: str
    status: PresentationStatus
    summary: str
    data: Mapping[str, JsonValue]
    follow_ups: tuple[ToolInvocation, ...]
    images: tuple[PresentationImage, ...] = Field(default=(), exclude=True)


class PresentationTemplate(PresentationValue):
    operation_id: str
    application: str
    package: str
    markdown_path: str
    structured_path: str


class McpPresentation(PresentationValue):
    markdown: str
    structured_content: PresentationEnvelope

    def is_error(self) -> bool:
        return self.structured_content.status is PresentationStatus.ERROR
