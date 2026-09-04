from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ..adapters import ScaffoldingsAdapter
from ..registry.model import Project
from ..workspaces.model import WorkspaceBinding
from .adapters import FilesystemAdapter
from .model import GenerationResult


@injectable
@dataclass(frozen=True)
class GenerationService:
    filesystem: FilesystemAdapter
    scaffoldings: ScaffoldingsAdapter

    def generate(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        destination: str,
        parameters: Mapping[str, JsonValue],
    ) -> GenerationResult:
        rendered_files = self.scaffoldings.render(project.scaffolding_id, parameters)
        written_files = self.filesystem.write(workspace.root, destination, rendered_files)
        return GenerationResult(files=written_files)
