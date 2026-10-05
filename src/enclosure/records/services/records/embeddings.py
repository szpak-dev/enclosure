import hashlib
import json
import math
import re
from dataclasses import dataclass

from django.conf import settings
from pydantic import JsonValue
from wireup import injectable

from ...errors import RecordsError
from .model import Embedding, UnavailableEmbedding, VectorEmbedding


@injectable
@dataclass(frozen=True)
class RecordsEmbeddingsService:
    def embed_record(self, title: str, content: JsonValue) -> Embedding:
        return self._embed(f"{title}\n{self._serialize(content)}")

    def embed_resource(self, path: str, language: str, content: str) -> Embedding:
        return self._embed(f"{path}\n{language}\n{content}")

    def embed_query(self, query: str) -> Embedding:
        return self._embed(query)

    def _embed(self, text: str) -> Embedding:
        if not settings.RECORDS_EMBEDDINGS_ENABLED:
            return UnavailableEmbedding()
        if settings.RECORDS_EMBEDDING_PROVIDER != "deterministic":
            raise RecordsError(f"Unsupported: {settings.RECORDS_EMBEDDING_PROVIDER!r}.")

        dimensions = settings.RECORDS_EMBEDDING_DIMENSIONS
        if dimensions <= 0:
            raise RecordsError("Records embedding dimensions must be positive.")

        vector = [0.0] * dimensions
        for token in re.findall(r"\w+", text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, byteorder="big")
            vector[value % dimensions] += 1.0 if value & 1 else -1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        values = vector if magnitude == 0 else [value / magnitude for value in vector]
        return VectorEmbedding(values=tuple(values))

    def _serialize(self, content: JsonValue) -> str:
        return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
