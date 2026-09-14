from dataclasses import dataclass
from importlib.resources import files
from pathlib import PurePosixPath
from typing import ClassVar

from wireup import injectable


@injectable
@dataclass(frozen=True)
class AgentInstructionsAdapter:
    package: ClassVar[str] = "enclosure.mcp"
    resource: ClassVar[str] = "resources/agent-bootstrap.md"

    def read(self) -> str:
        return files(self.package).joinpath(*PurePosixPath(self.resource).parts).read_text(encoding="utf-8")
