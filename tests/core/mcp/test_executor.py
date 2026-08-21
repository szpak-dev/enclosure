import json

import pytest
from httpx import Client, MockTransport, Request, Response
from sirenity import SirenMcpOperation, siren_configuration

from enclosure.core.mcp.executor import SirenExecutionError, SirenExecutor


def build_executor(transport: MockTransport) -> tuple[SirenExecutor, Client]:
    configuration = siren_configuration(
        openapi="enclosure.core.api.api",
        source_path="/api",
        public_path="/siren",
        policy="sirenity.SirenAllowAllPolicy",
    )
    client = Client(transport=transport, base_url="http://testserver")
    return SirenExecutor(configuration.adapter(), client), client


def test_executes_a_normalized_operation_against_the_json_application() -> None:
    def respond(request: Request) -> Response:
        assert request.method == "POST"
        assert request.url.path == "/api/diagrams/example-one/commands"
        assert dict(request.url.params) == {"page": "2"}
        assert request.headers["accept"] == "application/json"
        assert request.headers["example-trace"] == "trace-one"
        assert request.headers["cookie"] == "example-session=session-one"
        assert json.loads(request.content) == {
            "expected_revision": 1,
            "operation": "example-operation",
            "arguments": {},
        }
        return Response(
            200,
            json={"id": "example-one", "revision": 2},
            headers={"etag": '"revision-two"'},
        )

    executor, client = build_executor(MockTransport(respond))
    with client:
        result = executor.execute(
            SirenMcpOperation(
                operation_id="apply_diagram_command",
                path_values={"diagram_id": "example-one"},
                body={
                    "expected_revision": 1,
                    "operation": "example-operation",
                    "arguments": {},
                },
                query_values={"page": 2},
                header_values={"example-trace": "trace-one"},
                cookie_values={"example-session": "session-one"},
            )
        )

    assert result.status == 200
    assert result.result == {"id": "example-one", "revision": 2}
    assert result.base_url == "http://testserver"
    assert result.request_url == "http://testserver/api/diagrams/example-one/commands?page=2"
    assert result.headers["etag"] == '"revision-two"'


def test_preserves_application_errors_for_sirenity_projection() -> None:
    executor, client = build_executor(
        MockTransport(
            lambda _: Response(
                404,
                json={"detail": "Example resource not found."},
            )
        )
    )
    with client:
        result = executor.execute(
            SirenMcpOperation(
                operation_id="get_language",
                path_values={"language_id": "missing-example"},
            )
        )

    assert result.status == 404
    assert result.result == {"detail": "Example resource not found."}


def test_rejects_unknown_normalized_operations() -> None:
    executor, client = build_executor(MockTransport(lambda _: Response(204)))
    with client, pytest.raises(SirenExecutionError, match="Unknown Siren operation"):
        executor.execute(SirenMcpOperation(operation_id="missing_operation"))
