from collections.abc import Mapping
from dataclasses import dataclass

from mermaiden.diagrams import domain
from pydantic import JsonValue
from wireup import injectable

from .....errors import DiagramsError
from ....mermaiden.service import MermaidenService


@injectable
@dataclass(frozen=True)
class DiagramSnapshotRestorationService:
    mermaiden: MermaidenService

    def restore(
        self,
        kind: str,
        snapshot: Mapping[str, JsonValue],
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> domain.DiagramModel:
        current_identity = self.mermaiden.snapshot_contract_identity(kind)
        if (
            snapshot_version != current_identity.snapshot_version
            or registry_fingerprint != current_identity.registry_fingerprint
        ):
            raise DiagramsError("Archived diagram snapshot contract identity is not supported by this runtime.")
        diagram = self.mermaiden.restore(snapshot)
        if diagram.kind != kind:
            raise DiagramsError("Archived diagram snapshot kind does not match its accepted contract evidence.")
        return diagram
