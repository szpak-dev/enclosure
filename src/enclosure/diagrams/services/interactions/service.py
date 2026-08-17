from dataclasses import dataclass

from wireup import injectable

from ...errors import DiagramsError
from ...models import Diagram
from ..editing import DiagramEditingService
from ..mermaiden import MermaidenService
from ..validation import DiagramValidationService


@injectable
@dataclass(frozen=True)
class DiagramInteractionService:
    editing: DiagramEditingService
    mermaiden: MermaidenService
    validation: DiagramValidationService

    def update(self, id: str, expected_revision: int, value: object) -> Diagram:
        stored = self.editing.get(id)
        interactions = self.validation.interactions(value)
        diagram = self.mermaiden.restore(stored.snapshot)
        missing = set(interactions) - self.mermaiden.element_ids(diagram)
        if missing:
            names = ", ".join(sorted(missing))
            raise DiagramsError(f"Interaction targets do not exist in diagram {id!r}: {names}.")
        return self.editing.update(id, expected_revision, {"interactions": interactions})
