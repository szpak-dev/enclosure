import json

from httpx import Client, MockTransport, Request, Response
from sirenity import SirenMcpOperation

from enclosure.core.mcp.executor import SirenExecutor


def build_executor(transport: MockTransport) -> tuple[SirenExecutor, Client]:
    client = Client(transport=transport, base_url="http://testserver")
    return SirenExecutor(client), client


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
                method="POST",
                dispatch_path="/api/diagrams/example-one/commands",
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
                method="GET",
                dispatch_path="/api/languages/missing-example",
                path_values={"language_id": "missing-example"},
            )
        )

    assert result.status == 404
    assert result.result == {"detail": "Example resource not found."}


def test_dispatches_the_public_operation_target_without_adapter_route_lookup() -> None:
    def respond(request: Request) -> Response:
        assert request.method == "DELETE"
        assert request.url.path == "/api/example-resources/example-one"
        return Response(204)

    executor, client = build_executor(MockTransport(respond))
    with client:
        result = executor.execute(
            SirenMcpOperation(
                operation_id="operation_not_known_to_enclosure",
                method="DELETE",
                dispatch_path="/api/example-resources/example-one",
            )
        )

    assert result.status == 204
    assert result.result is None
