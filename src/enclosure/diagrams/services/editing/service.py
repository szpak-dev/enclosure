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
from ..validation import DiagramValidationService


@injectable
@dataclass(frozen=True)
class DiagramEditingService:
    repository: DiagramsRepository
    diagram_sets: DiagramSetService
    mermaiden: MermaidenService
    validation: DiagramValidationService

    def create(self, diagram_set_id: str, data: Mapping[str, object]) -> Diagram:
        self.diagram_sets.get(diagram_set_id)
        values = self.validation.diagram_creation(data)
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
        stored = self.require_revision(id, expected_revision)
        diagram = self.mermaiden.restore(stored.snapshot)
        self.mermaiden.apply(diagram, operation, arguments)
        return self.update(
            stored,
            {"snapshot": self.mermaiden.snapshot(diagram), "source": self.mermaiden.render(diagram)},
        )

    def require_revision(self, id: str, expected_revision: int) -> Diagram:
        expected_revision = self.validation.expected_revision(expected_revision)
        stored = self.get(id)
        if stored.revision != expected_revision:
            self._stale(id, expected_revision, stored.revision)
        return stored

    def update(self, stored: Diagram, data: Mapping[str, object]) -> Diagram:
        updated = self.repository.update_diagram(stored.id, stored.revision, data)
        if updated is None:
            current = self.get(stored.id)
            self._stale(stored.id, stored.revision, current.revision)
        return updated

    def delete(self, id: str) -> None:
        self.get(id)
        self.repository.delete_diagram(id)

    @staticmethod
    def _stale(id: str, expected: int, actual: int) -> Never:
        raise DiagramsError(
            f"Diagram {id!r} revision conflict: expected {expected}, current revision is {actual}."
        )
