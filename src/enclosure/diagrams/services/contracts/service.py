import json
from dataclasses import dataclass
from hashlib import sha256

from pydantic import JsonValue
from wireup import injectable

from ...errors import DiagramsError
from ..editing.service import DiagramEditingService
from ..mermaiden.service import MermaidenService
from .model import DiagramContractSnapshot


@injectable
@dataclass(frozen=True)
class DiagramContractService:
    editing: DiagramEditingService
    mermaiden: MermaidenService

    def resolve(
        self,
        diagram_set_id: str,
        diagram_id: str,
        expected_revision: int,
    ) -> DiagramContractSnapshot:
        stored = self.editing.get_in_set(diagram_set_id, diagram_id)
        if stored.revision != expected_revision:
            raise DiagramsError(
                f"Diagram {diagram_id!r} revision conflict: expected {expected_revision}, "
                f"current revision is {stored.revision}."
            )
        snapshot: dict[str, JsonValue] = stored.snapshot
        canonical = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        identity = self.mermaiden.snapshot_contract_identity(stored.kind)
        return DiagramContractSnapshot(
            diagram_id=str(stored.id),
            diagram_set_id=str(stored.diagram_set_id),
            revision=stored.revision,
            kind=stored.kind,
            draft=snapshot["draft"],
            snapshot=snapshot,
            snapshot_digest=sha256(canonical.encode("utf-8")).hexdigest(),
            snapshot_version=identity.snapshot_version,
            registry_fingerprint=identity.registry_fingerprint,
        )
