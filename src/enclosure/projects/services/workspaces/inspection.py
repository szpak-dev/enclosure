from dataclasses import dataclass
from pathlib import Path

from wireup import injectable

from ...errors import ProjectsError
from .model import WorkspaceBinding, WorkspaceLocation, WorkspaceState, WorkspaceStatus


@injectable
@dataclass(frozen=True)
class WorkspaceInspectionService:
    def normalize(self, root: str, architecture_root: str) -> WorkspaceLocation:
        if not root.strip() or not architecture_root.strip():
            raise ProjectsError("Workspace root and architecture root are required.")

        root_path = Path(root).expanduser()
        architecture_path = Path(architecture_root).expanduser()
        if not root_path.is_absolute() or not architecture_path.is_absolute():
            raise ProjectsError("Workspace root and architecture root must be absolute paths.")

        normalized_root = root_path.resolve()
        normalized_architecture_root = architecture_path.resolve()
        if not normalized_architecture_root.is_relative_to(normalized_root):
            raise ProjectsError("Architecture root must be within the workspace root.")
        if len(str(normalized_root)) > 1024 or len(str(normalized_architecture_root)) > 1024:
            raise ProjectsError("Workspace paths must not exceed 1024 characters.")

        return WorkspaceLocation(
            root=str(normalized_root),
            architecture_root=str(normalized_architecture_root),
        )

    def inspect(self, workspace: WorkspaceBinding) -> WorkspaceStatus:
        root = Path(workspace.root)
        architecture_root = Path(workspace.architecture_root)
        if not root.is_dir():
            state = WorkspaceState.MISSING_ROOT
        elif not architecture_root.is_dir():
            state = WorkspaceState.MISSING_ARCHITECTURE_ROOT
        else:
            state = WorkspaceState.AVAILABLE
        return WorkspaceStatus(workspace=workspace, state=state)
