from abc import ABC, abstractmethod
from typing import Literal

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


class Embedding(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @abstractmethod
    def vector(self) -> list[float] | None:
        raise NotImplementedError


class UnavailableEmbedding(Embedding):
    kind: Literal["unavailable"] = "unavailable"

    def vector(self) -> None:
        return None


class VectorEmbedding(Embedding):
    kind: Literal["vector"] = "vector"
    values: tuple[float, ...]

    def vector(self) -> list[float]:
        return list(self.values)


class RecordResourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    language: str
    content: str
    embedding: Embedding


class RecordCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    content: dict[str, JsonValue]
    category_id: str
    schema_version: int
    tag_ids: tuple[str, ...]
    resources: tuple[RecordResourceCandidate, ...]
    embedding: Embedding
