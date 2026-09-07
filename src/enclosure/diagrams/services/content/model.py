from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DiagramContentDocument(StrEnum):
    SOURCE = "source"
    SNAPSHOT = "snapshot"


class DiagramContentPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    revision: int
    document: DiagramContentDocument
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int
