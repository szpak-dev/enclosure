from dataclasses import dataclass, field
from typing import Any

from mermaiden.application import Application
from wireup import injectable

from .errors import DiagramsError


@injectable
@dataclass(frozen=True)
class DiagramsService:
    _application: Application = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_application", Application.create())

    def get_ids(self) -> list[str]:
        return [diagram.id for diagram in self._application.available_diagrams()]

    def get_schema(self, diagram_id: str) -> dict[str, Any]:
        for diagram in self._application.available_diagrams():
            if diagram.id != diagram_id:
                continue
            for configuration in self._application.mermaid_diagram_configs():
                if configuration.config_key == diagram.config_key:
                    return configuration.schema
            raise DiagramsError(f"No configuration schema is available for diagram ID: {diagram_id!r}")
        raise DiagramsError(f"Unsupported diagram ID: {diagram_id!r}")

    def recognize(self, content: str) -> None:
        syntax = self._syntax(content)
        if syntax in self.get_ids():
            return
        raise DiagramsError(f"Unsupported diagram syntax: {syntax!r}")

    @staticmethod
    def _syntax(content: str) -> str:
        lines = content.splitlines()
        first = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first is not None and lines[first].strip() == "---":
            closing = next((index for index in range(first + 1, len(lines)) if lines[index].strip() == "---"), None)
            if closing is None:
                raise DiagramsError("Diagram frontmatter is not closed.")
            lines = lines[closing + 1 :]

        for line in lines:
            syntax = line.strip()
            if syntax and syntax != "---":
                return syntax.split(maxsplit=1)[0]
        raise DiagramsError("Diagram content is empty.")
