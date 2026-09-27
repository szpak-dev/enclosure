from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from wireup import injectable

from enclosure.diagrams.errors import DiagramsError
from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics
from enclosure.diagrams.services.facade import DiagramsService

from ...errors import ProjectsError
from ..architecture_contracts.model import ArchitectureContractDiagram
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

    def interpret(
        self,
        diagram: ArchitectureContractDiagram,
    ) -> DiagramContractSemantics:
        try:
            return self.diagrams.interpret_contract_snapshot(
                diagram.kind,
                diagram.snapshot,
                diagram.snapshot_version,
                diagram.registry_fingerprint,
            )
        except DiagramsError as error:
            raise ProjectsError("Architecture diagram contract semantics could not be interpreted.") from error
