from collections.abc import Mapping
from dataclasses import dataclass

from mermaiden.diagrams import domain
from pydantic import JsonValue
from wireup import injectable

from .....errors import DiagramsError
from ....mermaiden import MermaidenService


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
        if snapshot_version < 1 or snapshot_version > current_identity.snapshot_version:
            raise DiagramsError("Archived diagram snapshot contract identity is not supported by this runtime.")
        if snapshot["version"] != snapshot_version or snapshot["kind"] != kind:
            raise DiagramsError("Archived diagram snapshot does not match its accepted contract evidence.")
        candidate = dict(snapshot)
        if snapshot_version == current_identity.snapshot_version:
            if registry_fingerprint != current_identity.registry_fingerprint:
                raise DiagramsError("Archived diagram snapshot contract identity is not supported by this runtime.")
        else:
            current = self.mermaiden.capture(self.mermaiden.create(kind)).snapshot
            configuration = dict(snapshot["configuration"])
            current_fields = current["configuration"]["fields"]
            configuration["fields"] = {
                **current_fields,
                **{name: value for name, value in configuration["fields"].items() if name in current_fields},
            }
            candidate["version"] = current_identity.snapshot_version
            candidate["configuration"] = configuration
            if "update_annotation" not in self.mermaiden.describe_kind(kind)["commands"]:
                candidate["annotations"] = []
        diagram = self.mermaiden.restore(candidate)
        if diagram.kind != kind:
            raise DiagramsError("Archived diagram snapshot kind does not match its accepted contract evidence.")
        return diagram
