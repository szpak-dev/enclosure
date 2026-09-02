from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentBootstrap:
    uri: str
    release: str
    revision: str
    markdown: str
