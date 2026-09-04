from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..registry.model import Project


class WorkspaceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str
    architecture_root: str


class WorkspaceBinding(WorkspaceLocation):
    id: str
    project_id: str
    revision: int


class WorkspaceState(StrEnum):
    AVAILABLE = "available"
    MISSING_ROOT = "missing_root"
    MISSING_ARCHITECTURE_ROOT = "missing_architecture_root"


class WorkspaceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: WorkspaceBinding
    state: WorkspaceState


class WorkspaceResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project: Project
    workspace: WorkspaceBinding
