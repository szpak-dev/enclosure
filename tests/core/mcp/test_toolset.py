from modwire_siren import SirenAdapter, siren_adapter

from enclosure.core.api import api
from enclosure.core.mcp.toolset import SirenToolset


def build_adapter() -> SirenAdapter:
    return siren_adapter(
        api.get_openapi_schema(path_prefix="/api"),
        source_path="/api",
        public_path="/siren",
    )


def test_exposes_every_siren_operation_as_a_tool() -> None:
    adapter = build_adapter()

    tools = SirenToolset(adapter).tools()

    assert [tool.name for tool in tools] == [route.operation_id for route in adapter.routes]


def test_preserves_the_compiled_operation_input_schema() -> None:
    tools = {tool.name: tool for tool in SirenToolset(build_adapter()).tools()}

    schema = tools["create_scaffolding"].input_schema

    assert schema["required"] == ["language_id", "name", "description", "spec"]
    assert schema["properties"]["language_id"] == {
        "description": "Language identifier for the rendered source code.",
        "title": "Language Id",
        "type": "string",
    }
    assert schema["properties"]["spec"]["type"] == "object"


def test_adds_siren_route_parameters_to_the_input_schema() -> None:
    tools = {tool.name: tool for tool in SirenToolset(build_adapter()).tools()}

    schema = tools["get_language"].input_schema

    assert schema == {
        "type": "object",
        "properties": {
            "language_id": {
                "type": "string",
                "description": "Path parameter for /siren/languages/{language_id}.",
            }
        },
        "required": ["language_id"],
    }
