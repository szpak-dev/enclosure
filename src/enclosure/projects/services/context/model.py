from typing import Literal

from pydantic import BaseModel, ConfigDict

from ..adapters.model import WorkspaceGuidance


class WorkspaceAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["project-record-bindings"]
    id: str
    revision: str


class WorkspaceContextDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    guidance_ids: tuple[str, ...]


class WorkspaceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    root: str
    readiness: Literal["ready", "incomplete", "conflicted"]
    authority: WorkspaceAuthority
    guidance: tuple[WorkspaceGuidance, ...]
    diagnostics: tuple[WorkspaceContextDiagnostic, ...]
