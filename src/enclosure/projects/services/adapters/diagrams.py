from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from wireup import injectable

from enclosure.diagrams.errors import DiagramsError
from enclosure.diagrams.services.facade import DiagramsService

from ...errors import ProjectsError
from .model import ResolvedArchitectureDiagram


@injectable
@dataclass(frozen=True)
class DiagramContractsAdapter:
    diagrams: DiagramsService

    def resolve(
        self,
        diagram_set_id: str,
        diagram_id: str,
        expected_revision: int,
    ) -> ResolvedArchitectureDiagram:
        try:
            resolved = self.diagrams.resolve_contract_snapshot(
                diagram_set_id,
                diagram_id,
                expected_revision,
            )
        except (DiagramsError, ObjectDoesNotExist) as error:
            raise ProjectsError(
                f"Architecture diagram {diagram_id!r} could not be resolved at revision {expected_revision}."
            ) from error
        return ResolvedArchitectureDiagram.model_validate(resolved.model_dump(mode="python"))
