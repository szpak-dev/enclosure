from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ...models import DiagramOrderField, SortDirection


class DiagramSetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str
    created_at: datetime
    updated_at: datetime


class DiagramSetPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[DiagramSetSummary, ...]
    has_more: bool
    next_offset: int
    limit: int
    order_by: DiagramOrderField
    direction: SortDirection
