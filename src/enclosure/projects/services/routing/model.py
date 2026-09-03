from pydantic import BaseModel, ConfigDict

from ..adapters.model import WorkspaceGuidance


class GuidanceScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    project_id: str
    record_id: str
    position: int


class GuidanceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: WorkspaceGuidance
    position: int


class GuidanceRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: tuple[WorkspaceGuidance, ...]
    missing_mandatory_ids: tuple[str, ...]
