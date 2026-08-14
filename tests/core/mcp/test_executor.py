import asyncio
import json
from collections.abc import Mapping
from typing import Any

from httpx import ASGITransport, AsyncClient, MockTransport, Request, Response
from sirenity import SirenAdapter, siren_adapter

from enclosure.core.api import api
from enclosure.core.asgi import application
from enclosure.core.mcp.executor import SirenExecutionError, SirenExecutor


def build_adapter() -> SirenAdapter:
    return siren_adapter(
        api.get_openapi_schema(path_prefix="/api"),
        source_path="/api",
        public_path="/siren",
    )


def execute(
    name: str,
    arguments: Mapping[str, Any],
    *,
    transport: ASGITransport | MockTransport | None = None,
):
    async def call():
        selected_transport = transport or ASGITransport(app=application)
        async with AsyncClient(transport=selected_transport, base_url="http://testserver") as client:
            return await SirenExecutor(build_adapter(), client).execute(name, arguments)

    return asyncio.run(call())


def test_executes_a_siren_operation_with_path_parameters() -> None:
    result = execute("get_language", {"language_id": "python"})

    assert result.is_error is False
    assert result.structured_content["class"] == ["language"]
    assert result.structured_content["properties"]["id"] == "python"
    assert json.loads(result.content[0].text) == result.structured_content


def test_returns_a_structured_siren_error() -> None:
    result = execute("get_language", {"language_id": "missing"})

    assert result.is_error is True
    assert result.structured_content == {
        "class": ["error"],
        "title": "Get a language",
        "properties": {"detail": "Resource not found.", "status": 404},
        "links": [
            {
                "rel": ["self"],
                "title": "Get a language",
                "href": "http://testserver/siren/languages/missing",
            }
        ],
    }


def test_sends_body_arguments_to_the_siren_route() -> None:
    async def respond(request: Request) -> Response:
        assert request.method == "POST"
        assert request.url.path == "/siren/projects/discoveries"
        assert request.headers["accept"] == "application/vnd.siren+json"
        assert json.loads(request.content) == {"root": "/project"}
        return Response(200, json={"class": ["project-discovery"]})

    result = execute(
        "discover_project",
        {"root": "/project"},
        transport=MockTransport(respond),
    )

    assert result.structured_content == {"class": ["project-discovery"]}


def test_rejects_calls_that_do_not_match_the_siren_contract() -> None:
    try:
        execute("get_language", {})
    except SirenExecutionError as error:
        assert str(error) == "Missing path parameter: language_id"
    else:
        raise AssertionError("SirenExecutionError was not raised")
