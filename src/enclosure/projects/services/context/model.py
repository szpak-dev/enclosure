from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..adapters.model import WorkspaceGuidance
from ..receipts.model import ContextReceipt


class WorkspaceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    root: str
    readiness: Literal["ready", "incomplete", "conflicted"]
    guidance: tuple[WorkspaceGuidance, ...]
    receipt: ContextReceipt
