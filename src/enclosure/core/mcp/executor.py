import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Any

from httpx import AsyncClient
from mcp.types import CallToolResult, TextContent
from sirenity import SirenAdapter

from enclosure.core.errors import DomainError

_SIREN_MEDIA_TYPE = "application/vnd.siren+json"
_PATH_PARAMETER = re.compile(r"\{([^}/]+)}")


class SirenExecutionError(DomainError): ...


@dataclass(frozen=True)
class SirenExecutor:
    adapter: SirenAdapter
    client: AsyncClient

    async def execute(
        self,
        name: str,
        arguments: Mapping[str, Any],
    ) -> CallToolResult:
        routes = [route for route in self.adapter.routes if route.operation_id == name]
        if len(routes) != 1:
            raise SirenExecutionError(f"Unknown Siren operation: {name}")
        route = routes[0]

        remaining = dict(arguments)
        path_values = {}
        for parameter in _PATH_PARAMETER.findall(route.public_path):
            if parameter not in remaining:
                raise SirenExecutionError(f"Missing path parameter: {parameter}")
            path_values[parameter] = remaining.pop(parameter)

        operation_input = self.adapter.engine.operation_input(name)
        body = {}
        query = {}
        headers = {"accept": _SIREN_MEDIA_TYPE}
        cookies = {}
        if operation_input is not None:
            body_properties = (
                operation_input.definition.get("properties", {})
                if operation_input.definition is not None
                else {}
            )
            for key in tuple(remaining):
                if key in body_properties:
                    body[key] = remaining.pop(key)
            for delegated in operation_input.delegated_inputs:
                if delegated.location == "body" or delegated.name not in remaining:
                    continue
                value = remaining.pop(delegated.name)
                if delegated.location == "query":
                    query[delegated.name] = value
                elif delegated.location == "header":
                    headers[delegated.name] = str(value)
                else:
                    cookies[delegated.name] = str(value)

        if remaining:
            names = ", ".join(sorted(remaining))
            raise SirenExecutionError(f"Unexpected arguments for {name}: {names}")
        if cookies:
            cookie = SimpleCookie(cookies)
            headers["cookie"] = "; ".join(morsel.OutputString() for morsel in cookie.values())

        response = await self.client.request(
            route.method,
            self.adapter.render_path(route.public_path, path_values),
            headers=headers,
            params=query,
            json=body if operation_input is not None else None,
        )
        document = response.json()
        if not isinstance(document, dict):
            raise SirenExecutionError(f"Siren operation returned a non-object document: {name}")

        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(document))],
            structured_content=document,
            is_error=response.is_error,
        )
