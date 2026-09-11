from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ..models import Diagram, DiagramSet
from .catalog import DiagramCatalogService
from .content import DiagramContentDocument, DiagramContentPage, DiagramContentService
from .diagram_sets.model import DiagramSetPage
from .diagram_sets.service import DiagramSetService
from .editing.model import DiagramPage
from .editing.service import DiagramEditingService


@injectable
@dataclass(frozen=True)
class DiagramsService:
    catalog: DiagramCatalogService
    content: DiagramContentService
    diagram_sets: DiagramSetService
    editing: DiagramEditingService

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

    def find_set_page(self, offset: int, limit: int) -> DiagramSetPage:
        return self.diagram_sets.find_page(offset, limit)

    def update_set(self, id: str, data: Mapping[str, object]) -> DiagramSet:
        return self.diagram_sets.update(id, data)

    def delete_set(self, id: str) -> None:
        self.diagram_sets.delete(id)

    def create_diagram(self, diagram_set_id: str, data: Mapping[str, object]) -> Diagram:
        return self.editing.create(diagram_set_id, data)

    def get_diagram(self, id: str) -> Diagram:
        return self.editing.get(id)

    def read_diagram_content(
        self,
        id: str,
        document: str,
        expected_revision: int,
        offset: int,
        limit: int,
    ) -> DiagramContentPage:
        return self.content.read(
            id,
            DiagramContentDocument(document),
            expected_revision,
            offset,
            limit,
        )

    def update_diagram(self, id: str, expected_revision: int, title: str) -> Diagram:
        return self.editing.rename(id, expected_revision, title)

    def get_diagram_in_set(self, diagram_set_id: str, id: str) -> Diagram:
        return self.editing.get_in_set(diagram_set_id, id)

    def find_all_diagrams(self) -> QuerySet[Diagram]:
        return self.editing.find_all()

    def find_diagram_page(self, offset: int, limit: int) -> DiagramPage:
        return self.editing.find_page(offset, limit)

    def find_diagrams_in_set(self, diagram_set_id: str) -> QuerySet[Diagram]:
        return self.editing.find_in_set(diagram_set_id)

    def find_diagram_set_page(self, diagram_set_id: str, offset: int, limit: int) -> DiagramPage:
        return self.editing.find_in_set_page(diagram_set_id, offset, limit)

    def apply_command(
        self,
        id: str,
        expected_revision: int,
        operation: str,
        arguments: Mapping[str, object],
    ) -> Diagram:
        return self.editing.apply(id, expected_revision, operation, arguments)

    def apply_command_batch(
        self,
        id: str,
        expected_revision: int,
        commands: Sequence[tuple[str, Mapping[str, object]]],
    ) -> dict[str, object]:
        return self.editing.apply_batch(id, expected_revision, commands)

    def delete_diagram(self, id: str) -> None:
        self.editing.delete(id)
