from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue

from ..operations import ToolInvocation


class PresentationValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    INCOMPLETE = "incomplete"


class PresentationEnvelope(PresentationValue):
    operation_id: str
    status: PresentationStatus
    summary: str
    data: Mapping[str, JsonValue]
    follow_ups: tuple[ToolInvocation, ...]


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
