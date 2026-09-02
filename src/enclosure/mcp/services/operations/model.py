from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, JsonValue


class McpValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolDefinition(McpValue):
    name: str
    title: str
    description: str
    input_schema: Mapping[str, JsonValue]


class ToolCatalogue(McpValue):
    fingerprint: str
    tools: tuple[ToolDefinition, ...]


class ToolInvocation(McpValue):
    operation_id: str
    arguments: Mapping[str, JsonValue]


class SirenDocument(McpValue):
    operation_id: str
    document: Mapping[str, JsonValue]
    is_error: bool
    classes: tuple[str, ...]
    title: str
    detail: str
