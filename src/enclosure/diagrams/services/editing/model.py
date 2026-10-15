from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from ...models import Diagram, DiagramOrderField, SortDirection


class DiagramPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[Diagram, ...]
    has_more: bool
    next_offset: int
    limit: int
    order_by: DiagramOrderField
    direction: SortDirection


@dataclass(frozen=True)
class DiagramBatchReceipt:
    diagram_id: str
    revision: int
    applied_count: int
