from collections.abc import Mapping
from dataclasses import dataclass, field

from mermaiden.diagrams import domain
from pydantic import JsonValue, ValidationError
from wireup import injectable

from .....errors import DiagramsError
from ....mermaiden.service import MermaidenService
from .model import ArchivedDiagramSnapshotContract, DiagramSnapshotEnvelope


@injectable
@dataclass(frozen=True)
class DiagramSnapshotRestorationService:
    mermaiden: MermaidenService
    contracts: tuple[ArchivedDiagramSnapshotContract, ...] = field(
        default=(
            ArchivedDiagramSnapshotContract(
                snapshot_version=6,
                registry_fingerprint="38d3ff340a880f0854042c4795db2eeab598c990ff244bfae7c4b035c48e3a1b",
                kinds=("classDiagram", "erDiagram", "treeView-beta"),
            ),
            ArchivedDiagramSnapshotContract(
                snapshot_version=7,
                registry_fingerprint="6e19987b9b38c43297098b7acc48149b5d684c055659ba460ae6a6273e6b9c30",
                kinds=("classDiagram", "erDiagram", "treeView-beta"),
            ),
        ),
        init=False,
    )

    def restore(
        self,
        kind: str,
        snapshot: Mapping[str, JsonValue],
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> domain.DiagramModel:
        current_identity = self.mermaiden.snapshot_contract_identity(kind)
        if (
            snapshot_version == current_identity.snapshot_version
            and registry_fingerprint == current_identity.registry_fingerprint
        ):
            diagram = self.mermaiden.restore(snapshot)
        else:
            supported = any(
                contract.accepts(kind, snapshot_version, registry_fingerprint) for contract in self.contracts
            )
            if not supported:
                raise DiagramsError("Archived diagram snapshot contract identity is not supported by this runtime.")
            try:
                archived = DiagramSnapshotEnvelope.model_validate(snapshot)
                current = DiagramSnapshotEnvelope.model_validate(
                    self.mermaiden.capture(self.mermaiden.create(kind)).snapshot
                )
            except ValidationError as error:
                raise DiagramsError("Archived diagram snapshot does not satisfy its envelope contract.") from error
            if archived.version != snapshot_version:
                raise DiagramsError("Archived diagram snapshot version does not match its accepted contract evidence.")
            if archived.kind != kind:
                raise DiagramsError("Archived diagram snapshot kind does not match its accepted contract evidence.")
            diagram = self.mermaiden.restore(archived.upgrade(current).document())
        if diagram.kind != kind:
            raise DiagramsError("Archived diagram snapshot kind does not match its accepted contract evidence.")
        return diagram
