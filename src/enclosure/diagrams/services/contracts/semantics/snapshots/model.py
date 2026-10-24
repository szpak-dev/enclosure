from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from .....errors import DiagramsError


class DiagramSnapshotConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)

    discriminator: str = Field(alias="$type")
    fields: dict[str, JsonValue]

    def document(self) -> dict[str, JsonValue]:
        return {
            "$type": self.discriminator,
            "fields": self.fields,
        }


class DiagramSnapshotEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: int
    kind: str
    draft: bool
    configuration: DiagramSnapshotConfiguration
    elements: list[dict[str, JsonValue]]
    relations: list[dict[str, JsonValue]]
    annotations: list[dict[str, JsonValue]]
    properties: dict[str, JsonValue]

    def upgrade(self, current: "DiagramSnapshotEnvelope") -> "DiagramSnapshotEnvelope":
        if self.kind != current.kind:
            raise DiagramsError("Archived diagram snapshot kind is not supported by the current contract.")
        if self.configuration.discriminator != current.configuration.discriminator:
            raise DiagramsError("Archived diagram snapshot configuration type is not supported by this runtime.")
        unexpected = self.configuration.fields.keys() - current.configuration.fields.keys()
        if unexpected:
            names = ", ".join(sorted(unexpected))
            raise DiagramsError(f"Archived diagram snapshot has unsupported configuration fields: {names}.")
        return DiagramSnapshotEnvelope(
            version=current.version,
            kind=self.kind,
            draft=self.draft,
            configuration=DiagramSnapshotConfiguration(
                **{
                    "$type": self.configuration.discriminator,
                    "fields": current.configuration.fields | self.configuration.fields,
                }
            ),
            elements=self.elements,
            relations=self.relations,
            annotations=self.annotations,
            properties=self.properties,
        )

    def document(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "kind": self.kind,
            "draft": self.draft,
            "configuration": self.configuration.document(),
            "elements": list(self.elements),
            "relations": list(self.relations),
            "annotations": list(self.annotations),
            "properties": self.properties,
        }


@dataclass(frozen=True)
class ArchivedDiagramSnapshotContract:
    snapshot_version: int
    registry_fingerprint: str
    kinds: tuple[str, ...]

    def accepts(
        self,
        kind: str,
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> bool:
        return (
            kind in self.kinds
            and snapshot_version == self.snapshot_version
            and registry_fingerprint == self.registry_fingerprint
        )
