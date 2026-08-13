from collections.abc import Mapping
from dataclasses import dataclass
from typing import Never

from django.db.models import QuerySet
from wireup import injectable

from ...errors import DiagramsError
from ...models import Diagram
from ..diagram_sets import DiagramSetService
from ..mermaiden import MermaidenService
from ..repository import DiagramsRepository


@injectable
@dataclass(frozen=True)
class DiagramEditingService:
    repository: DiagramsRepository
    diagram_sets: DiagramSetService
    mermaiden: MermaidenService

    def create(self, diagram_set_id: str, data: Mapping[str, object]) -> Diagram:
        self.diagram_sets.get(diagram_set_id)
        values = self._validate_creation(data)
        diagram = self.mermaiden.create(values["kind"])
        return self.repository.create_diagram(
            diagram_set_id,
            {
                **values,
                "snapshot": self.mermaiden.snapshot(diagram),
                "source": self.mermaiden.render(diagram),
            },
        )

    def get(self, id: str) -> Diagram:
        try:
            return self.repository.get_diagram(id)
        except Diagram.DoesNotExist as error:
            raise DiagramsError(f"Diagram {id!r} does not exist.") from error

    def find_all(self, diagram_set_id: str | None = None) -> QuerySet[Diagram]:
        if diagram_set_id is not None:
            self.diagram_sets.get(diagram_set_id)
        return self.repository.find_all_diagrams(diagram_set_id)

    def apply(
        self,
        id: str,
        expected_revision: int,
        operation: str,
        arguments: Mapping[str, object],
    ) -> Diagram:
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool) or expected_revision < 1:
            raise DiagramsError("Expected diagram revision must be a positive integer.")
        stored = self.get(id)
        if stored.revision != expected_revision:
            self._stale(id, expected_revision, stored.revision)

        diagram = self.mermaiden.restore(stored.snapshot)
        self.mermaiden.apply(diagram, operation, arguments)
        updated = self.repository.update_diagram(
            id,
            expected_revision,
            {
                "snapshot": self.mermaiden.snapshot(diagram),
                "source": self.mermaiden.render(diagram),
            },
        )
        if updated is None:
            current = self.get(id)
            self._stale(id, expected_revision, current.revision)
        return updated

    def delete(self, id: str) -> None:
        self.get(id)
        self.repository.delete_diagram(id)

    @staticmethod
    def _validate_creation(data: Mapping[str, object]) -> dict[str, str]:
        unknown = set(data) - {"title", "kind"}
        if unknown:
            names = ", ".join(sorted(unknown))
            raise DiagramsError(f"Unsupported diagram fields: {names}.")

        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise DiagramsError("Diagram title must be a non-empty string.")
        if len(title.strip()) > 255:
            raise DiagramsError("Diagram title must not exceed 255 characters.")

        kind = data.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise DiagramsError("Diagram kind must be a non-empty string.")
        if len(kind.strip()) > 64:
            raise DiagramsError("Diagram kind must not exceed 64 characters.")
        return {"title": title.strip(), "kind": kind.strip()}

    @staticmethod
    def _stale(id: str, expected: int, actual: int) -> Never:
        raise DiagramsError(
            f"Diagram {id!r} revision conflict: expected {expected}, current revision is {actual}."
        )
