from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sirenity import SirenMcpOperation

from enclosure.mcp.services.operations.adapters import http as http_adapter
from enclosure.mcp.services.operations.adapters import siren as siren_adapter
from enclosure.mcp.services.operations.adapters.http import HttpSirenExecutor
from enclosure.mcp.services.operations.adapters.siren import SirenGatewayAdapter
from enclosure.mcp.services.operations.model import ToolInvocation


def test_reuses_one_wsgi_application_for_warm_executions(monkeypatch: pytest.MonkeyPatch) -> None:
    applications: list[object] = []
    paths: list[str] = []

    def application(environ: dict[str, Any], start_response: Any) -> Iterable[bytes]:
        paths.append(environ["PATH_INFO"])
        start_response("204 No Content", [])
        return [b""]

    executor = HttpSirenExecutor()
    object.__setattr__(executor, "_application", application)
    transport = http_adapter.WSGITransport
    monkeypatch.setattr(
        http_adapter,
        "WSGITransport",
        lambda *, app: applications.append(app) or transport(app=app),
    )
    operation = SirenMcpOperation(operation_id="health", method="GET", dispatch_path="/health")

    first = executor.execute(operation)
    second = executor.execute(operation)

    assert applications == [application, application]
    assert paths == ["/health", "/health"]
    assert first.status == second.status == 204


def test_reuses_one_siren_configuration_and_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    configuration = object()
    executor = cast(HttpSirenExecutor, object())
    configuration_calls: list[dict[str, Any]] = []
    bridge_calls: list[tuple[object, HttpSirenExecutor]] = []

    class Bridge:
        catalogue_fingerprint = "example-fingerprint"

        def tools(self) -> tuple[()]:
            return ()

        def invoke(self, invocation: Any) -> SimpleNamespace:
            return SimpleNamespace(
                structured_content={"title": invocation.operation_id, "properties": {"detail": "ok"}},
                is_error=False,
            )

    def build_configuration(**declaration: Any) -> object:
        configuration_calls.append(declaration)
        return configuration

    def build_bridge(received: object, *, executor: HttpSirenExecutor) -> Bridge:
        bridge_calls.append((received, executor))
        return Bridge()

    monkeypatch.setattr(siren_adapter, "siren_configuration", build_configuration)
    monkeypatch.setattr(siren_adapter, "siren_mcp", build_bridge)
    gateway = SirenGatewayAdapter(executor=executor)

    catalogue = gateway.catalogue()
    document = gateway.invoke(ToolInvocation(operation_id="get_example", arguments={}))

    assert len(configuration_calls) == 1
    assert bridge_calls == [(configuration, executor)]
    assert catalogue.fingerprint == "example-fingerprint"
    assert document.title == "get_example"
    assert document.detail == "ok"


def test_surfaces_siren_configuration_failure_when_catalogue_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_configuration(**declaration: Any) -> object:
        raise RuntimeError("invalid Siren configuration")

    monkeypatch.setattr(siren_adapter, "siren_configuration", fail_configuration)
    gateway = SirenGatewayAdapter(executor=cast(HttpSirenExecutor, object()))

    with pytest.raises(RuntimeError, match="invalid Siren configuration"):
        gateway.catalogue()
