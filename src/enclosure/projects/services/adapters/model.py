from typing import NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, JsonValue


class GuidanceContent(TypedDict):
    authority: NotRequired[str]
    summary: NotRequired[str]
    applies_when: NotRequired[list[str]]
    guidance: NotRequired[list[str]]
    checks: NotRequired[list[str]]


class WorkspaceGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    summary: str
    authority: str
    revision: str
    schema_revision: int
    current_schema_revision: int
    applies_when: tuple[str, ...]
    guidance: tuple[str, ...]
    checks: tuple[str, ...]


class WorkspaceGuidanceResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: tuple[WorkspaceGuidance, ...]
    missing_ids: tuple[str, ...]


class GuidanceRanking(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    ordered_ids: tuple[str, ...]


class ResolvedArchitectureDiagram(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_set_id: str
    revision: int
    kind: str
    draft: bool
    snapshot: dict[str, JsonValue]
    snapshot_digest: str
    snapshot_version: int
    registry_fingerprint: str
