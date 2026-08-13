from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ..models import Diagram, DiagramSet
from .catalog import DiagramCatalogService
from .diagram_sets import DiagramSetService
from .editing import DiagramEditingService
from .interactions import DiagramInteractionService


@injectable
@dataclass(frozen=True)
class DiagramsService:
    catalog: DiagramCatalogService
    diagram_sets: DiagramSetService
    editing: DiagramEditingService
    interactions: DiagramInteractionService

    def find_kinds(self) -> tuple[dict[str, str], ...]:
        return self.catalog.find_kinds()

    def describe_kind(self, kind: str) -> dict[str, object]:
        return self.catalog.describe_kind(kind)

    def get_command_schema(self, kind: str, operation: str) -> dict[str, object]:
        return self.catalog.get_command_schema(kind, operation)

    def create_set(self, data: Mapping[str, object]) -> DiagramSet:
        return self.diagram_sets.create(data)

    def get_set(self, id: str) -> DiagramSet:
        return self.diagram_sets.get(id)

    def find_all_sets(self) -> QuerySet[DiagramSet]:
        return self.diagram_sets.find_all()

    def update_set(self, id: str, data: Mapping[str, object]) -> DiagramSet:
        return self.diagram_sets.update(id, data)

    def delete_set(self, id: str) -> None:
        self.diagram_sets.delete(id)

    def create_diagram(self, diagram_set_id: str, data: Mapping[str, object]) -> Diagram:
        return self.editing.create(diagram_set_id, data)

    def get_diagram(self, id: str) -> Diagram:
        return self.editing.get(id)

    def find_all_diagrams(self, diagram_set_id: str | None = None) -> QuerySet[Diagram]:
        return self.editing.find_all(diagram_set_id)

    def apply_command(
        self,
        id: str,
        expected_revision: int,
        operation: str,
        arguments: Mapping[str, object],
    ) -> Diagram:
        return self.editing.apply(id, expected_revision, operation, arguments)

    def update_interactions(self, id: str, expected_revision: int, value: object) -> Diagram:
        return self.interactions.update(id, expected_revision, value)

    def delete_diagram(self, id: str) -> None:
        self.editing.delete(id)
