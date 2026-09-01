from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from mermaiden import Application
from wireup import injectable

from ...errors import DiagramsError


@injectable
@dataclass(frozen=True)
class MermaidenService:
    _application: Application = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_application", Application.create())

    def find_kinds(self) -> tuple[dict[str, str], ...]:
        return tuple({"id": item.id, "name": item.name} for item in self._application.available_diagrams())

    def describe_kind(self, kind: str) -> dict[str, object]:
        try:
            return self._application.diagram_description(kind).model_dump(mode="json")
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def get_command_schema(self, kind: str, operation: str) -> dict[str, object]:
        try:
            return self._application.command_payload(kind, operation).model_json_schema()
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def create(self, kind: str) -> Any:
        try:
            return self._application.create_diagram(kind)
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def restore(self, snapshot: Mapping[str, object]) -> Any:
        try:
            return self._application.restore(snapshot)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def apply(
        self,
        diagram: Any,
        operation: str,
        arguments: Mapping[str, object],
    ) -> None:
        try:
            self._application.execute(diagram, operation, arguments)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def snapshot(self, diagram: Any) -> dict[str, object]:
        return self._application.snapshot(diagram).to_dict()

    def render(self, diagram: Any) -> str:
        return self._application.render(diagram)
