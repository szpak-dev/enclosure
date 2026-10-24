import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from typing import cast

import httpx2
import pytest
from django.test import Client
from django.test.utils import override_settings
from pytest_django.live_server_helper import LiveServer

from enclosure.core.asgi import ApplicationFactory

from ...support import (
    BlockingArchitectureSource,
    DisconnectingHealthRequest,
    accept_health_architecture,
    discover,
    distinguish_project_source,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthExecutionAttacks:
    @pytest.mark.health_serial
    @pytest.mark.django_db(transaction=True)
    def test_health_rejects_source_drift_before_returning_a_completed_report(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        live_server: LiveServer,
    ) -> None:
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "DriftApplication")
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        attack_started = Event()
        attack_stopped = Event()

        def mutate_source() -> None:
            revision = 0
            while not attack_stopped.is_set():
                replacement = tmp_path / ".app.py.replacement"
                replacement.write_text(f"class ChangedApplication{revision}:\n    pass\n", encoding="utf-8")
                os.replace(replacement, tmp_path / "app.py")
                attack_started.set()
                revision += 1
                sleep(0.001)

        with ThreadPoolExecutor(max_workers=1) as executor:
            attack = executor.submit(mutate_source)
            assert attack_started.wait(timeout=1)
            try:
                response = httpx2.get(f"{live_server.url}{path}", timeout=20)
            finally:
                attack_stopped.set()
                attack.result(timeout=5)

        assert response.status_code == 422
        assert response.json() == {"detail": "Project source changed during health evaluation."}

    @pytest.mark.health_serial
    @override_settings(PROJECT_HEALTH_MAX_CONCURRENCY=1)
    @pytest.mark.django_db(transaction=True)
    def test_health_rejects_excess_concurrency_and_recovers_capacity(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        source = BlockingArchitectureSource.create(tmp_path)
        source.replace()
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert client.get(path).status_code == 200
        source.block()
        with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=2):
            with ThreadPoolExecutor(max_workers=1) as executor:
                active_request = executor.submit(Client().get, path)
                writer = asyncio.run(asyncio.wait_for(source.connect_writer_when_ready(), timeout=5))
                try:
                    started = monotonic()
                    unavailable = client.get(path)
                    unavailable_duration = monotonic() - started
                    bounded = active_request.result(timeout=5)
                finally:
                    os.close(writer)

        source.replace()
        recovery_started = monotonic()
        with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=15):
            recovered = client.get(path)
        recovery_duration = monotonic() - recovery_started

        assert unavailable.status_code == 503
        assert unavailable.json() == {"detail": "Project health execution capacity is exhausted."}
        assert unavailable_duration < 1
        assert bounded.status_code == 504
        assert recovered.status_code == 200
        assert recovery_duration < 15

    @pytest.mark.health_serial
    @override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=1)
    @pytest.mark.django_db(transaction=True)
    def test_health_times_out_blocked_work_and_recovers_capacity(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        source = BlockingArchitectureSource.create(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        caplog.clear()
        started = monotonic()
        timed_out = client.get(path)
        timeout_duration = monotonic() - started
        source.replace()
        with override_settings(PROJECT_HEALTH_TIMEOUT_SECONDS=15):
            recovered = client.get(path)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]
        completed_run_id = next(
            event["run_id"]
            for event in events
            if event.get("event") == "project_health_terminal" and event["outcome"] == "completed"
        )
        replacement = next(
            event
            for event in events
            if event.get("event") == "project_health_worker_bootstrap_terminal" and event["run_id"] == completed_run_id
        )

        assert timed_out.status_code == 504
        assert timed_out.json() == {"detail": "Project health execution timed out."}
        # Contract resolution and process teardown occur outside the one-second worker deadline.
        assert 1 <= timeout_duration < 6
        assert recovered.status_code == 200
        assert replacement["replacement"] is True

    @pytest.mark.health_serial
    @pytest.mark.django_db(transaction=True)
    def test_health_disconnect_cancels_work_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        source = BlockingArchitectureSource.create(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )
        first_request = DisconnectingHealthRequest(
            application=ApplicationFactory().build(),
            path=path,
            source=source,
        )

        second_request = DisconnectingHealthRequest(
            application=ApplicationFactory().build(),
            path=path,
            source=source,
        )
        asyncio.run(first_request.run_before(second_request))
        recovered = client.get(path)
        terminal_events = [
            json.loads(line)
            for line in capfd.readouterr().err.splitlines()
            if '"event": "project_health_terminal"' in line
        ]
        canceled_events = [event for event in terminal_events if event["outcome"] == "canceled"]

        assert first_request.messages == []
        assert second_request.messages == []
        assert recovered.status_code == 200
        assert [event["outcome"] for event in terminal_events] == ["canceled", "canceled", "completed"]
        assert len(canceled_events) == 2
