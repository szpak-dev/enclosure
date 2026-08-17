from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ...core.models import DjangoRepository
from ..errors import DiagramsError
from ..models import Diagram, DiagramSet


@injectable
@dataclass
class DiagramsRepository(DjangoRepository[Diagram]):
    model: type[Diagram] = field(default=Diagram, init=False)

    def create_set(self, data: Mapping[str, Any]) -> DiagramSet:
        return DiagramSet.objects.create(**data)

    def get_set(self, id: str) -> DiagramSet:
        return DiagramSet.objects.get(pk=id)

    def find_all_sets(self) -> QuerySet[DiagramSet]:
        return DiagramSet.objects.all()

    def update_set(self, id: str, data: Mapping[str, Any]) -> DiagramSet:
        diagram_set = self.get_set(id)
        for attribute, value in data.items():
            setattr(diagram_set, attribute, value)
        diagram_set.save()
        return diagram_set

    def delete_set(self, id: str) -> None:
        self.get_set(id).delete()

    def create_diagram(self, diagram_set_id: str, data: Mapping[str, Any]) -> Diagram:
        return self.model.objects.create(diagram_set_id=diagram_set_id, **data)

    def get_diagram(self, id: str) -> Diagram:
        return self.find_all_diagrams().get(pk=id)

    def get_diagram_in_set(self, diagram_set_id: str, id: str) -> Diagram:
        return self.find_diagrams_in_set(diagram_set_id).get(pk=id)

    def find_all_diagrams(self) -> QuerySet[Diagram]:
        return self.model.objects.select_related("diagram_set")

    def find_diagrams_in_set(self, diagram_set_id: str) -> QuerySet[Diagram]:
        return self.find_all_diagrams().filter(diagram_set_id=diagram_set_id)

    @transaction.atomic
    def update_diagram(self, id: str, expected_revision: int, data: Mapping[str, Any]) -> Diagram:
        diagram = self.model.objects.select_for_update().get(pk=id)
        if diagram.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {diagram.revision}."
            )
        for attribute, value in data.items():
            setattr(diagram, attribute, value)
        diagram.revision += 1
        diagram.save()
        return diagram

    def delete_diagram(self, id: str) -> None:
        self.get_diagram(id).delete()
