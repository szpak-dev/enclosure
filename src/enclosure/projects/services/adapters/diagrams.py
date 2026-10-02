from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from wireup import injectable

from enclosure.diagrams.errors import DiagramsError
from enclosure.diagrams.services.contracts.semantics.model import DiagramContractSemantics
from enclosure.diagrams.services.facade import DiagramsService

from ...errors import ProjectsError
from ..architecture_contracts.model import ArchitectureContractDiagramContract
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
        return ResolvedArchitectureDiagram(
            diagram_id=resolved.diagram_id,
            diagram_set_id=resolved.diagram_set_id,
            revision=resolved.revision,
            kind=resolved.kind,
            draft=resolved.draft,
            snapshot=resolved.snapshot,
            snapshot_digest=resolved.snapshot_digest,
            snapshot_version=resolved.snapshot_version,
            registry_fingerprint=resolved.registry_fingerprint,
        )

    def interpret(
        self,
        diagram: ArchitectureContractDiagramContract,
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
