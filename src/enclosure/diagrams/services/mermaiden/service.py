from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from mermaiden import Application
from mermaiden.core.domain import DiagramSnapshotContractIdentity
from mermaiden.diagrams import domain
from wireup import injectable

from ...errors import DiagramsError


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

    def restore(self, snapshot: Mapping[str, object]) -> domain.DiagramModel:
        try:
            return self._application.restore(snapshot)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def apply(
        self,
        diagram: domain.DiagramModel,
        operation: str,
        arguments: Mapping[str, object],
    ) -> None:
        try:
            self._application.execute(diagram, operation, arguments)
        except RuntimeError as error:
            raise DiagramsError(str(error)) from error

    def apply_batch(
        self,
        diagram: domain.DiagramModel,
        commands: Sequence[tuple[str, Mapping[str, object]]],
    ) -> None:
        payload = tuple({"operation": operation, "arguments": arguments} for operation, arguments in commands)
        try:
            self._application.apply_batch(diagram, payload)
        except (RuntimeError, ValueError) as error:
            raise DiagramsError(str(error)) from error

    def snapshot(self, diagram: domain.DiagramModel) -> dict[str, object]:
        return self._application.snapshot(diagram).to_dict()

    def snapshot_contract_identity(self, kind: str) -> DiagramSnapshotContractIdentity:
        return self._application.snapshot_contract_identity(kind)

    def render(self, diagram: domain.DiagramModel) -> str:
        return self._application.render(diagram)
