from pydantic import BaseModel, ConfigDict


class DiagramSvgPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    revision: int
    filename: str
    media_type: str
    content_revision: str
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int
