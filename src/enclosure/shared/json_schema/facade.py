from dataclasses import dataclass
from typing import Any

from wireup import injectable

from .schema import Schema
from .validator import JsonSchemaValidator


@injectable
@dataclass(frozen=True)
class JsonSchemaService:
    validator: JsonSchemaValidator

    def load(self, document: dict[str, Any]) -> Schema:
        canonical_document = {"$schema": "https://json-schema.org/draft/2020-12/schema", **document}
        self.validator.require_valid_schema(canonical_document)
        return Schema(canonical_document, self.validator)
