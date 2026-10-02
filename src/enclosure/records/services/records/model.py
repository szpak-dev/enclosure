from pydantic import BaseModel, ConfigDict, JsonValue


class RecordResourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    language: str
    content: str


class RecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    content: dict[str, JsonValue]
    category_id: str
    tag_ids: tuple[str, ...]
    resources: tuple[RecordResourceInput, ...]


class RecordResourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    language: str
    content: str
    embedding: list[float] | None


class RecordCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    content: dict[str, JsonValue]
    category_id: str
    schema_version: int
    tag_ids: tuple[str, ...]
    resources: tuple[RecordResourceCandidate, ...]
    embedding: list[float] | None
