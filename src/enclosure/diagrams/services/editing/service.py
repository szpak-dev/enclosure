from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...errors import DiagramsError
from ...models import Diagram, DiagramOrdering
from ..diagram_sets.service import DiagramSetService
from ..mermaiden.model import DiagramCommand
from ..mermaiden.service import MermaidenService
from ..repository import DiagramsRepository
from .model import DiagramBatchReceipt, DiagramPage


@injectable
@dataclass(frozen=True)
class DiagramEditingService:
    repository: DiagramsRepository
    diagram_sets: DiagramSetService
    mermaiden: MermaidenService

    def create(self, diagram_set_id: str, title: str, kind: str) -> Diagram:
        self.diagram_sets.get(diagram_set_id)
        diagram = self.mermaiden.create(kind)
        state = self.mermaiden.capture(diagram)
        return self.repository.create_diagram(
            diagram_set_id,
            title,
            kind,
            state.snapshot,
            state.source,
        )

    def create_batch(
        self,
        diagram_set_id: str,
        title: str,
        kind: str,
        commands: tuple[DiagramCommand, ...],
    ) -> DiagramBatchReceipt:
        self.diagram_sets.get(diagram_set_id)
        diagram = self.mermaiden.create(kind)
        self.mermaiden.apply_batch(diagram, commands)
        state = self.mermaiden.capture(diagram)
        created = self.repository.create_diagram(
            diagram_set_id,
            title,
            kind,
            state.snapshot,
            state.source,
        )
        return DiagramBatchReceipt(
            diagram_id=str(created.id),
            revision=created.revision,
            applied_count=len(commands),
        )

    def get(self, id: str) -> Diagram:
        return self.repository.get_diagram(id)

    def rename(self, id: str, expected_revision: int, title: str) -> Diagram:
        return self.repository.rename_diagram(id, expected_revision, title)

    def get_in_set(self, diagram_set_id: str, id: str) -> Diagram:
        return self.repository.get_diagram_in_set(diagram_set_id, id)

    def find_all(self) -> QuerySet[Diagram]:
        return self.repository.find_all_diagrams()

    def find_page(self, offset: int, limit: int, ordering: DiagramOrdering) -> DiagramPage:
        diagrams = tuple(self.repository.find_diagram_page(offset, limit, ordering))
        items = diagrams[:limit]
        return DiagramPage(
            items=items,
            has_more=len(diagrams) > limit,
            next_offset=offset + len(items),
            limit=limit,
            order_by=ordering.field,
            direction=ordering.direction,
        )

    def find_in_set(self, diagram_set_id: str) -> QuerySet[Diagram]:
        self.diagram_sets.get(diagram_set_id)
        return self.repository.find_diagrams_in_set(diagram_set_id)

    def find_in_set_page(
        self,
        diagram_set_id: str,
        offset: int,
        limit: int,
        ordering: DiagramOrdering,
    ) -> DiagramPage:
        self.diagram_sets.get(diagram_set_id)
        diagrams = tuple(self.repository.find_diagram_set_page(diagram_set_id, offset, limit, ordering))
        items = diagrams[:limit]
        return DiagramPage(
            items=items,
            has_more=len(diagrams) > limit,
            next_offset=offset + len(items),
            limit=limit,
            order_by=ordering.field,
            direction=ordering.direction,
        )

    def apply(
        self,
        id: str,
        expected_revision: int,
        command: DiagramCommand,
    ) -> Diagram:
        stored = self.get(id)
        if stored.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {stored.revision}."
            )
        diagram = self.mermaiden.restore(stored.snapshot)
        self.mermaiden.apply(diagram, command)
        state = self.mermaiden.capture(diagram)
        return self.repository.replace_diagram_content(
            id,
            expected_revision,
            state.snapshot,
            state.source,
        )

    def apply_batch(
        self,
        id: str,
        expected_revision: int,
        commands: tuple[DiagramCommand, ...],
    ) -> DiagramBatchReceipt:
        stored = self.get(id)
        if stored.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {stored.revision}."
            )
        diagram = self.mermaiden.restore(stored.snapshot)
        self.mermaiden.apply_batch(diagram, commands)
        state = self.mermaiden.capture(diagram)
        updated = self.repository.replace_diagram_content(
            id,
            expected_revision,
            state.snapshot,
            state.source,
        )
        return DiagramBatchReceipt(
            diagram_id=str(updated.id),
            revision=updated.revision,
            applied_count=len(commands),
        )

    def delete(self, id: str) -> None:
        self.repository.delete_diagram(id)
