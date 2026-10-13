from collections.abc import Mapping
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet
from pydantic import JsonValue
from wireup import injectable

from ...core.models import DjangoRepository
from ..errors import DiagramsError
from ..models import Diagram, DiagramSet


@injectable
@dataclass
class DiagramsRepository(DjangoRepository[Diagram]):
    model: type[Diagram] = field(default=Diagram, init=False)

    def create_set(self, title: str, description: str) -> DiagramSet:
        return DiagramSet.objects.create(title=title, description=description)

    def get_set(self, id: str) -> DiagramSet:
        return DiagramSet.objects.get(pk=id)

    def find_all_sets(self) -> QuerySet[DiagramSet]:
        return DiagramSet.objects.order_by("id")

    def find_set_page(self, offset: int, limit: int) -> QuerySet[DiagramSet]:
        return self.find_all_sets()[offset : offset + limit + 1]

    def replace_set(self, id: str, title: str, description: str) -> DiagramSet:
        diagram_set = self.get_set(id)
        diagram_set.title = title
        diagram_set.description = description
        diagram_set.save()
        return diagram_set

    def delete_set(self, id: str) -> None:
        self.get_set(id).delete()

    def create_diagram(
        self,
        diagram_set_id: str,
        title: str,
        kind: str,
        snapshot: Mapping[str, JsonValue],
        source: str,
    ) -> Diagram:
        return self.model.objects.create(
            diagram_set_id=diagram_set_id,
            title=title,
            kind=kind,
            snapshot=snapshot,
            source=source,
        )

    def get_diagram(self, id: str) -> Diagram:
        return self.find_all_diagrams().get(pk=id)

    def get_diagram_in_set(self, diagram_set_id: str, id: str) -> Diagram:
        return self.find_diagrams_in_set(diagram_set_id).get(pk=id)

    def find_all_diagrams(self) -> QuerySet[Diagram]:
        return self.model.objects.select_related("diagram_set").order_by("id")

    def find_diagram_page(self, offset: int, limit: int) -> QuerySet[Diagram]:
        return self.find_all_diagrams()[offset : offset + limit + 1]

    def find_diagrams_in_set(self, diagram_set_id: str) -> QuerySet[Diagram]:
        return self.find_all_diagrams().filter(diagram_set_id=diagram_set_id)

    def find_diagram_set_page(self, diagram_set_id: str, offset: int, limit: int) -> QuerySet[Diagram]:
        return self.find_diagrams_in_set(diagram_set_id)[offset : offset + limit + 1]

    @transaction.atomic
    def rename_diagram(self, id: str, expected_revision: int, title: str) -> Diagram:
        diagram = self.model.objects.select_for_update().get(pk=id)
        if diagram.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {diagram.revision}."
            )
        diagram.title = title
        diagram.revision += 1
        diagram.save()
        return diagram

    @transaction.atomic
    def replace_diagram_content(
        self,
        id: str,
        expected_revision: int,
        snapshot: Mapping[str, JsonValue],
        source: str,
    ) -> Diagram:
        diagram = self.model.objects.select_for_update().get(pk=id)
        if diagram.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {diagram.revision}."
            )
        diagram.snapshot = snapshot
        diagram.source = source
        diagram.revision += 1
        diagram.save()
        return diagram

    def delete_diagram(self, id: str) -> None:
        self.get_diagram(id).delete()
