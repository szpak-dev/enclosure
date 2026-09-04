from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from wireup import injectable

from ... import models
from ...errors import ProjectsError
from .model import WorkspaceLocation


@injectable
@dataclass
class WorkspaceRepository:
    model: type[models.WorkspaceBinding] = field(default=models.WorkspaceBinding, init=False)

    def get_by_root(self, root: str) -> models.WorkspaceBinding:
        return self.model.objects.select_related("project").get(root=root)

    def find(self, project_id: str) -> QuerySet[models.WorkspaceBinding]:
        return self.model.objects.filter(project_id=project_id).order_by("root")

    def get(self, project_id: str, workspace_id: str) -> models.WorkspaceBinding:
        return self.model.objects.get(project_id=project_id, pk=workspace_id)

    def create(self, project_id: str, location: WorkspaceLocation) -> models.WorkspaceBinding:
        try:
            return self.model.objects.create(
                project_id=project_id,
                root=location.root,
                architecture_root=location.architecture_root,
            )
        except IntegrityError as error:
            raise ProjectsError(f"Workspace root is already bound: {location.root}") from error

    @transaction.atomic
    def replace(
        self,
        project_id: str,
        workspace_id: str,
        location: WorkspaceLocation,
        expected_revision: int,
    ) -> models.WorkspaceBinding:
        workspace = self.model.objects.select_for_update().get(project_id=project_id, pk=workspace_id)
        self._require_revision(workspace, expected_revision)
        workspace.root = location.root
        workspace.architecture_root = location.architecture_root
        workspace.revision += 1
        try:
            workspace.save(update_fields=("root", "architecture_root", "revision"))
        except IntegrityError as error:
            raise ProjectsError(f"Workspace root is already bound: {location.root}") from error
        return workspace

    @transaction.atomic
    def delete(self, project_id: str, workspace_id: str, expected_revision: int) -> None:
        workspace = self.model.objects.select_for_update().get(project_id=project_id, pk=workspace_id)
        self._require_revision(workspace, expected_revision)
        workspace.delete()

    def _require_revision(self, workspace: models.WorkspaceBinding, expected_revision: int) -> None:
        if workspace.revision != expected_revision:
            raise ProjectsError(
                f"Workspace {workspace.id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {workspace.revision}."
            )
