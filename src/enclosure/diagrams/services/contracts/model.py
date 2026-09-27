from pydantic import BaseModel, ConfigDict, JsonValue


class DiagramContractSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_set_id: str
    revision: int
    kind: str
    draft: bool
    snapshot: dict[str, JsonValue]
    snapshot_digest: str
    snapshot_version: int
    registry_fingerprint: str
