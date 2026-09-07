import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from ...operations import SirenDocument


@injectable
@dataclass(frozen=True)
class SirenProjectionService:
    MAX_STRING_CHARACTERS: ClassVar[int] = 512
    MAX_CONTAINER_BYTES: ClassVar[int] = 7_000
    MAX_SCHEMA_BYTES: ClassVar[int] = 7_000
    MAX_SUMMARY_KEYS: ClassVar[int] = 64

    def project(self, document: SirenDocument) -> Mapping[str, JsonValue]:
        if "collection" in document.classes:
            entities = document.document.get("entities", ())
            data = self._collection(entities)
        else:
            data = self._properties(document.document)
        self._navigation(document.document, data)
        return data

    def _collection(
        self,
        entities: Sequence[Mapping[str, JsonValue]],
    ) -> dict[str, JsonValue]:
        items: list[JsonValue] = []
        for entity in entities:
            item = self._properties(entity)
            self._self_link(entity, item)
            items.append(item)
        return {
            "count": len(entities),
            "items": items,
        }

    def _navigation(self, document: Mapping[str, JsonValue], data: dict[str, JsonValue]) -> None:
        actions = [
            {
                "name": action["name"],
                "method": action["method"],
                "href": action["href"],
            }
            for action in document.get("actions", ())
        ]
        links = [
            {name: link[name] for name in ("rel", "title", "href") if name in link}
            for link in document.get("links", ())
        ]
        if actions:
            data["actions"] = actions
        if links:
            data["links"] = links

    def _self_link(self, entity: Mapping[str, JsonValue], item: dict[str, JsonValue]) -> None:
        for link in entity.get("links", ()):
            if "self" in link["rel"]:
                item["href"] = link["href"]
                return

    def _properties(self, entity: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        projected = {}
        for name, item in entity.get("properties", {}).items():
            result = self._value(item, False)
            if result is not None:
                projected[str(name)] = result
        return projected

    def _value(self, value: JsonValue, schema: bool) -> JsonValue:
        match value:
            case Mapping():
                return self._mapping(value, schema)
            case str():
                if len(value) <= self.MAX_STRING_CHARACTERS:
                    return value
                return f"{value[: self.MAX_STRING_CHARACTERS - 3]}..."
            case list() | tuple():
                projected = [self._value(item, schema) for item in value]
                if self._encoded_size(projected) > self._container_limit(schema):
                    return {
                        "summary": "collection",
                        "count": len(value),
                    }
                return projected
            case _:
                return value

    def _mapping(
        self,
        value: Mapping[str, JsonValue],
        schema: bool,
    ) -> dict[str, JsonValue]:
        schema = schema or self._is_json_schema(value)
        projected = {}
        for name, item in value.items():
            result = self._value(item, schema)
            if result is not None:
                projected[str(name)] = result
        if self._encoded_size(projected) > self._container_limit(schema):
            return self._mapping_summary(projected)
        return projected

    def _mapping_summary(self, value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        scalar_values = {}
        for name, item in value.items():
            match item:
                case str() | int() | float() | bool() | None:
                    scalar_values[name] = item
        return {
            "summary": "object",
            "count": len(value),
            "keys": list(value)[: self.MAX_SUMMARY_KEYS],
            "values": scalar_values,
        }

    def _container_limit(self, schema: bool) -> int:
        return self.MAX_SCHEMA_BYTES if schema else self.MAX_CONTAINER_BYTES

    def _encoded_size(self, value: JsonValue) -> int:
        return len(
            json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )

    def _is_json_schema(self, value: Mapping[object, object]) -> bool:
        keys = {str(name) for name in value}
        return "$defs" in keys or "$schema" in keys or bool({"properties", "oneOf", "anyOf", "allOf"} & keys)
