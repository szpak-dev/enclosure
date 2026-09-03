from typing import Literal

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


class GuidanceBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selected: tuple[GuidanceCandidate, ...]
    omitted_ids: tuple[str, ...]
    used_characters: int
    limit_characters: int


class GuidanceRouteItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: WorkspaceGuidance
    requirement: Literal["mandatory", "supplemental"]
    reason: Literal["operating-contract", "task-applicable", "project-default"]


class GuidanceRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[GuidanceRouteItem, ...]
    missing_mandatory_ids: tuple[str, ...]
    omitted_optional_ids: tuple[str, ...]
    used_optional_characters: int
    optional_character_limit: int
