from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.db.models import QuerySet
from wireup import injectable

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
                **self._persistence_values(diagram),
            },
        )

    def get(self, id: str) -> Diagram:
        return self.repository.get_diagram(id)

    def get_in_set(self, diagram_set_id: str, id: str) -> Diagram:
        return self.repository.get_diagram_in_set(diagram_set_id, id)

    def find_all(self) -> QuerySet[Diagram]:
        return self.repository.find_all_diagrams()

    def find_in_set(self, diagram_set_id: str) -> QuerySet[Diagram]:
        self.diagram_sets.get(diagram_set_id)
        return self.repository.find_diagrams_in_set(diagram_set_id)

    def apply(
        self,
        id: str,
        expected_revision: int,
        operation: str,
        arguments: Mapping[str, object],
    ) -> Diagram:
        stored = self.get(id)
        diagram = self.mermaiden.restore(stored.snapshot)
        self.mermaiden.apply(diagram, operation, arguments)
        return self.update(
            id,
            expected_revision,
            self._persistence_values(diagram),
        )

    def _persistence_values(self, diagram: Any) -> dict[str, object]:
        snapshot = self.mermaiden.snapshot(diagram)
        return {
            "snapshot": snapshot,
            "source": "" if snapshot.get("draft") is True else self.mermaiden.render(diagram),
        }

    def update(
        self,
        id: str,
        expected_revision: int,
        data: Mapping[str, object],
    ) -> Diagram:
        revision = self.validation.expected_revision(expected_revision)
        return self.repository.update_diagram(id, revision, data)

    def delete(self, id: str) -> None:
        self.repository.delete_diagram(id)
