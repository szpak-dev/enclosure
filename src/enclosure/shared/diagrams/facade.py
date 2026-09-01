from dataclasses import dataclass, field
from typing import Any

from mermaiden import Application
from wireup import injectable

from .errors import DiagramsError

# Legacy Records resource-validation boundary. The first-class diagrams Django
# app owns diagram persistence and editing through its own Mermaiden integration.


@injectable
@dataclass(frozen=True)
class DiagramsService:
    _application: Application = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_application", Application.create())

    def get_ids(self) -> list[str]:
        return [diagram.id for diagram in self._application.available_diagrams()]

    def get_schema(self, diagram_id: str) -> dict[str, Any]:
        try:
            return self._application.command_payload(diagram_id, "configure").model_json_schema()
        except KeyError as error:
            raise DiagramsError(f"Unsupported diagram ID: {diagram_id!r}") from error

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
