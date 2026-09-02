from collections.abc import Mapping
from dataclasses import dataclass

from django.conf import settings
from pydantic import JsonValue
from sirenity import (
    SirenConfiguration,
    SirenMcpInvocation,
    siren_configuration,
    siren_mcp,
)
from wireup import injectable

from ..gateway import SirenGateway
from ..model import SirenDocument, ToolCatalogue, ToolDefinition, ToolInvocation
from .http import HttpSirenExecutor


@injectable(as_type=SirenGateway)
@dataclass(frozen=True)
class SirenGatewayAdapter(SirenGateway):
    executor: HttpSirenExecutor

    def catalogue(self) -> ToolCatalogue:
        bridge = siren_mcp(self._configuration(), executor=self.executor)
        return ToolCatalogue(
            fingerprint=bridge.catalogue_fingerprint,
            tools=tuple(
                ToolDefinition(
                    name=tool.name,
                    title=tool.title,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
                for tool in bridge.tools()
            ),
        )

    def invoke(self, invocation: ToolInvocation) -> SirenDocument:
        bridge = siren_mcp(self._configuration(), executor=self.executor)
        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id=invocation.operation_id,
                arguments=invocation.arguments,
            )
        )
        document = dict(result.structured_content)
        properties = document.get("properties")
        details = properties if isinstance(properties, Mapping) else document
        return SirenDocument(
            operation_id=invocation.operation_id,
            document=document,
            is_error=result.is_error,
            classes=self._classes(document),
            title=self._text(document.get("title")),
            detail=self._text(details.get("detail")),
        )

    def _configuration(self) -> SirenConfiguration:
        declaration = settings.SIRENITY
        if isinstance(declaration, SirenConfiguration):
            return declaration
        return siren_configuration(
            openapi=declaration["OPENAPI"],
            source_path=declaration["SOURCE_PATH"],
            public_path=declaration["PUBLIC_PATH"],
            policy=declaration["POLICY"],
            profiles=tuple(declaration["PROFILES"]),
        )

    def _classes(self, document: Mapping[str, JsonValue]) -> tuple[str, ...]:
        classes = document.get("class")
        if not isinstance(classes, list):
            return ()
        return tuple(value for value in classes if isinstance(value, str))

    def _text(self, value: JsonValue) -> str:
        return value if isinstance(value, str) else ""
