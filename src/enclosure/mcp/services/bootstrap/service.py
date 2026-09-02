import hashlib
import os
from dataclasses import dataclass
from typing import ClassVar

from wireup import injectable

from .model import AgentBootstrap
from .repository import BootstrapRepository

MAX_BOOTSTRAP_BYTES = 8_192


@injectable
@dataclass(frozen=True)
class AgentBootstrapService:
    repository: BootstrapRepository
    release: ClassVar[str] = os.getenv("ENCLOSURE_RUNTIME_VERSION", "0.0.0+dev")

    def instructions(self) -> str:
        return (
            "Enclosure provides project operating context and architecture checks. "
            "Call get_workspace_context before working in a registered workspace."
        )

    def load(self) -> AgentBootstrap:
        markdown = self.repository.read()
        content = markdown.encode("utf-8")
        if not markdown.strip():
            raise ValueError("The MCP agent bootstrap is empty.")
        if len(content) > MAX_BOOTSTRAP_BYTES:
            raise ValueError(f"The MCP agent bootstrap exceeds {MAX_BOOTSTRAP_BYTES} bytes.")
        return AgentBootstrap(
            uri="pkg://enclosure.mcp/resources/agent-bootstrap.md",
            release=self.release,
            revision=hashlib.sha256(content).hexdigest(),
            markdown=markdown,
        )
