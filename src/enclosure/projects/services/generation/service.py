from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.scaffoldings.services.renderings.model import RenderedFile

from ..adapters import ScaffoldingsAdapter
from ..registry.model import Project
from ..workspaces.model import WorkspaceBinding
from .adapters import AgentInstructionsAdapter, FilesystemAdapter
from .model import GenerationResult


@injectable
@dataclass(frozen=True)
class GenerationService:
    agent_instructions: AgentInstructionsAdapter
    filesystem: FilesystemAdapter
    scaffoldings: ScaffoldingsAdapter

    def install_agent_instructions(self, workspace: WorkspaceBinding) -> GenerationResult:
        written_files = self.filesystem.write(
            workspace.root,
            "",
            (
                RenderedFile(
                    path="AGENTS.md",
                    content=self.agent_instructions.read(),
                    overwrite=True,
                ),
            ),
        )
        return GenerationResult(files=written_files)

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
