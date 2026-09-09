from pydantic import BaseModel, ConfigDict

from ...models import Diagram


class DiagramPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[Diagram, ...]
    has_more: bool
    next_offset: int
    limit: int
