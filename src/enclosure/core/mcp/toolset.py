import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from mcp.types import Tool
from sirenity import SirenAdapter, SirenOperationInput

from enclosure.core.errors import DomainError

_PATH_PARAMETER = re.compile(r"\{([^}/]+)}")


class SirenToolsetError(DomainError): ...


@dataclass(frozen=True)
class SirenToolset:
    adapter: SirenAdapter

    def tools(self) -> list[Tool]:
        return [
            Tool(
                name=route.operation_id,
                title=route.operation_id.replace("_", " ").title(),
                description=f"{route.method} {route.public_path}",
                input_schema=self._input_schema(
                    route.public_path,
                    self.adapter.engine.operation_input(route.operation_id),
                ),
            )
            for route in self.adapter.routes
        ]

    @staticmethod
    def _input_schema(
        path: str,
        operation_input: SirenOperationInput | None,
    ) -> dict[str, Any]:
        schema = (
            deepcopy(dict(operation_input.definition))
            if operation_input is not None and operation_input.definition is not None
            else {"type": "object", "properties": {}}
        )
        if schema.get("type") != "object":
            raise SirenToolsetError("MCP tool input schemas must have an object root")

        properties = dict(schema.get("properties", {}))
        required = list(schema.get("required", []))

        if operation_input is not None:
            for delegated in operation_input.delegated_inputs:
                if delegated.location == "body" or delegated.name in properties:
                    continue
                properties[delegated.name] = deepcopy(
                    dict(delegated.definition)
                    if delegated.definition is not None
                    else {"type": delegated.kind}
                )
                if delegated.required and delegated.name not in required:
                    required.append(delegated.name)

        for name in _PATH_PARAMETER.findall(path):
            if name in properties:
                raise SirenToolsetError(f"Path parameter conflicts with operation input: {name}")
            properties[name] = {
                "type": "string",
                "description": f"Path parameter for {path}.",
            }
            required.append(name)

        schema["properties"] = properties
        if required:
            schema["required"] = required
        return schema
