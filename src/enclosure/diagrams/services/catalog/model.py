from pydantic import BaseModel, ConfigDict


class DiagramKindContentPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    revision: str
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int
