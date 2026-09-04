from dataclasses import dataclass

from wireup import injectable

from ..registry.service import RegistryService
from .inspection import WorkspaceInspectionService
from .model import WorkspaceBinding, WorkspaceLocation, WorkspaceResolution, WorkspaceStatus
from .repository import WorkspaceRepository


@injectable
@dataclass(frozen=True)
class WorkspaceService:
    registry: RegistryService
    repository: WorkspaceRepository
    inspection: WorkspaceInspectionService

    def resolve(self, root: str) -> WorkspaceResolution:
        normalized = self.inspection.normalize(root, root)
        workspace = self._workspace(self.repository.get_by_root(normalized.root))
        return WorkspaceResolution(
            project=self.registry.get(workspace.project_id),
            workspace=workspace,
        )

    def find(self, project_id: str) -> tuple[WorkspaceBinding, ...]:
        self.registry.get(project_id)
        return tuple(self._workspace(workspace) for workspace in self.repository.find(project_id))

    def get(self, project_id: str, workspace_id: str) -> WorkspaceBinding:
        self.registry.get(project_id)
        return self._workspace(self.repository.get(project_id, workspace_id))

    def bind(self, project_id: str, location: WorkspaceLocation) -> WorkspaceBinding:
        self.registry.get(project_id)
        normalized = self.inspection.normalize(location.root, location.architecture_root)
        return self._workspace(self.repository.create(project_id, normalized))

    def replace(
        self,
        project_id: str,
        workspace_id: str,
        location: WorkspaceLocation,
        expected_revision: int,
    ) -> WorkspaceBinding:
        self.registry.get(project_id)
        normalized = self.inspection.normalize(location.root, location.architecture_root)
        return self._workspace(self.repository.replace(project_id, workspace_id, normalized, expected_revision))

    def inspect(self, project_id: str, workspace_id: str) -> WorkspaceStatus:
        return self.inspection.inspect(self.get(project_id, workspace_id))

    def delete(self, project_id: str, workspace_id: str, expected_revision: int) -> None:
        self.registry.get(project_id)
        self.repository.delete(project_id, workspace_id, expected_revision)

    def _workspace(self, workspace: object) -> WorkspaceBinding:
        return WorkspaceBinding.model_validate(workspace, from_attributes=True)
