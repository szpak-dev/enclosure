from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ..adapters import ScaffoldingsAdapter
from ..repository import ProjectRepository
from .adapters import FilesystemAdapter
from .model import GenerationResult


@injectable
@dataclass(frozen=True)
class GenerationService:
    filesystem: FilesystemAdapter
    repository: ProjectRepository
    scaffoldings: ScaffoldingsAdapter

    def generate(
        self,
        project_id: str,
        destination: str,
        parameters: Mapping[str, JsonValue],
    ) -> GenerationResult:
        project = self.repository.get(project_id)
        rendered_files = self.scaffoldings.render(project.scaffolding_id, parameters)
        written_files = self.filesystem.write(project.root, destination, rendered_files)
        return GenerationResult(files=written_files)
