from collections.abc import Mapping
from dataclasses import dataclass, field

from mermaiden import Application
from mermaiden.core.domain import DiagramSnapshotContractIdentity
from mermaiden.diagrams import domain
from pydantic import JsonValue
from wireup import injectable

from ...errors import DiagramsError
from .model import DiagramCommand, DiagramState


@injectable
@dataclass(frozen=True)
class MermaidenService:
    _application: Application = field(default_factory=Application.create, init=False, repr=False)

    def find_kinds(self) -> tuple[dict[str, str], ...]:
        return tuple({"id": item.id, "name": item.name} for item in self._application.available_diagrams())

    def describe_kind(self, kind: str) -> dict[str, object]:
        try:
            return self._application.diagram_description(kind).model_dump(mode="json")
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def get_command_schema(self, kind: str, operation: str) -> dict[str, object]:
        try:
            return self._application.command_payload(kind, operation).schema()
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def create(self, kind: str) -> domain.DiagramModel:
        try:
            return self._application.create_diagram(kind)
        except KeyError as error:
            raise DiagramsError(str(error)) from error

    def restore(self, snapshot: Mapping[str, JsonValue]) -> domain.DiagramModel:
        try:
            return self._application.restore(snapshot)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def apply(
        self,
        diagram: domain.DiagramModel,
        command: DiagramCommand,
    ) -> None:
        try:
            self._application.execute(diagram, command.operation, command.arguments)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def apply_batch(
        self,
        diagram: domain.DiagramModel,
        commands: tuple[DiagramCommand, ...],
    ) -> None:
        payload = tuple({"operation": command.operation, "arguments": command.arguments} for command in commands)
        try:
            self._application.apply_batch(diagram, payload)
        except (RuntimeError, ValueError) as error:
            raise DiagramsError(str(error)) from error

    def capture(self, diagram: domain.DiagramModel) -> DiagramState:
        snapshot = self._application.snapshot(diagram).to_dict()
        source = "" if snapshot["draft"] is True else self._application.render(diagram)
        return DiagramState(snapshot=snapshot, source=source)

    def snapshot_contract_identity(self, kind: str) -> DiagramSnapshotContractIdentity:
        return self._application.snapshot_contract_identity(kind)
