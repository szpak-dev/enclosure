from dataclasses import dataclass
from functools import cached_property
from typing import Any

from django.conf import settings
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
        return ToolCatalogue(
            fingerprint=self._bridge.catalogue_fingerprint,
            tools=tuple(
                ToolDefinition(
                    name=tool.name,
                    title=tool.title,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
                for tool in self._bridge.tools()
            ),
        )

    def invoke(self, invocation: ToolInvocation) -> SirenDocument:
        result = self._bridge.invoke(
            SirenMcpInvocation(
                operation_id=invocation.operation_id,
                arguments=invocation.arguments,
            )
        )
        document = dict(result.structured_content)
        properties = document.get("properties", document)
        return SirenDocument(
            operation_id=invocation.operation_id,
            arguments=invocation.arguments,
            document=document,
            is_error=result.is_error,
            classes=tuple(document.get("class", ())),
            title=document.get("title", ""),
            detail=properties.get("detail", ""),
        )

    @cached_property
    def _bridge(self) -> Any:
        declaration = settings.SIRENITY
        configuration: SirenConfiguration = siren_configuration(
            openapi=declaration["OPENAPI"],
            source_path=declaration["SOURCE_PATH"],
            public_path=declaration["PUBLIC_PATH"],
            policy=declaration["POLICY"],
            profiles=tuple(declaration["PROFILES"]),
        )
        return siren_mcp(configuration, executor=self.executor)
