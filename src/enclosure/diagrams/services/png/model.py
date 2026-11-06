from pydantic import BaseModel, ConfigDict


class DiagramPng(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    revision: int
    filename: str
    media_type: str
    content_revision: str
    content: str
    width: int
    height: int
    total_bytes: int
