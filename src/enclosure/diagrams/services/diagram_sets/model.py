from pydantic import BaseModel, ConfigDict

from ...models import DiagramSet


class DiagramSetPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    items: tuple[DiagramSet, ...]
    has_more: bool
    next_offset: int
    limit: int
