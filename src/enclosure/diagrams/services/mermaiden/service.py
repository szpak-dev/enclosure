from collections.abc import Mapping
from dataclasses import dataclass, field

from mermaiden.application import Application, DiagramCommand, UnknownCommand
from mermaiden.core import ChangeRejected, OperationError
from mermaiden.diagrams.domain import DiagramModel
from mermaiden.runtime.snapshot import SnapshotError
from wireup import injectable

from ...errors import DiagramsError


@injectable
@dataclass(frozen=True)
class MermaidenService:
    _application: Application = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_application", Application.create())

    def create(self, kind: str) -> DiagramModel:
        try:
            return self._application.create_diagram(kind)
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def restore(self, snapshot: Mapping[str, object]) -> DiagramModel:
        try:
            return self._application.restore(snapshot)
        except (KeyError, SnapshotError, TypeError, ValueError) as error:
            raise DiagramsError(str(error)) from error

    def apply(
        self,
        diagram: DiagramModel,
        operation: str,
        arguments: Mapping[str, object],
    ) -> None:
        try:
            self._application.apply(diagram, DiagramCommand(operation, arguments))
        except (ChangeRejected, OperationError, UnknownCommand) as error:
            raise DiagramsError(str(error)) from error

    def snapshot(self, diagram: DiagramModel) -> dict[str, object]:
        return self._application.snapshot(diagram).to_dict()

    def render(self, diagram: DiagramModel) -> str:
        try:
            return self._application.render(diagram)
        except (ChangeRejected, OperationError, ValueError) as error:
            raise DiagramsError(str(error)) from error
