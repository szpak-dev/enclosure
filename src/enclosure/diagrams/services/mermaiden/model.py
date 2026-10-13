from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue


@dataclass(frozen=True)
class DiagramCommand:
    operation: str
    arguments: Mapping[str, JsonValue]


@dataclass(frozen=True)
class DiagramState:
    snapshot: Mapping[str, JsonValue]
    source: str
