from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    title: str
    description: str
    input_schema: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ToolCatalogue:
    fingerprint: str
    tools: tuple[ToolDefinition, ...]


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    operation_id: str
    arguments: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SirenDocument:
    operation_id: str
    document: Mapping[str, JsonValue]
    is_error: bool
    classes: tuple[str, ...]
    title: str | None
    detail: str | None
