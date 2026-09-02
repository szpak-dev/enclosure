import hashlib
from dataclasses import dataclass

from wireup import injectable

from .model import AgentBootstrap
from .repository import BootstrapRepository


@injectable
@dataclass(frozen=True, slots=True)
class AgentBootstrapService:
    repository: BootstrapRepository
    release: str = "0.0.0+dev"

    def instructions(self) -> str:
        return (
            "Enclosure provides project operating context and architecture checks. "
            "Call get_workspace_context before working in a registered workspace."
        )

    def load(self) -> AgentBootstrap:
        markdown = self.repository.read()
        revision = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        return AgentBootstrap(
            uri="enclosure://guidance/agent-bootstrap",
            release=self.release,
            revision=revision,
            markdown=markdown,
        )
