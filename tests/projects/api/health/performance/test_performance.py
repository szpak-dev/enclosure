from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import cast

import pytest
from django.test import Client

from ...support import (
    COMPLETE_BOUNDARIES_YAML,
    COMPLETE_SHAPE_YAML,
    accept_health_architecture,
    discover,
    distinguish_project_source,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthPerformanceInvariants:
    @pytest.mark.health_serial
    @pytest.mark.django_db
    def test_health_is_insensitive_to_one_hundred_thousand_excluded_files(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        record_property: Callable[[str, object], None],
    ) -> None:
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "ScaleApplication")
        payload = registration(discover(client, tmp_path), dependencies, shape_yaml=COMPLETE_SHAPE_YAML)
        payload["boundaries_yaml"] = COMPLETE_BOUNDARIES_YAML
        resolution = client.post(
            "/api/projects",
            data=payload,
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )
        baseline = client.get(path)
        noise = tmp_path / ".dev" / "noise"
        creation_started = monotonic()
        for directory_index in range(100):
            directory = noise / str(directory_index)
            directory.mkdir(parents=True)
            for file_index in range(1000):
                (directory / str(file_index)).touch()
        creation_duration = monotonic() - creation_started

        caplog.clear()
        started = monotonic()
        repeated = client.get(path)
        duration = monotonic() - started
        record_property("file_creation_seconds", creation_duration)
        record_property("health_seconds", duration)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]

        assert baseline.status_code == 200, baseline.json()
        assert repeated.status_code == 200, repeated.json()
        assert repeated.json() == baseline.json()
        assert duration < 5
        assert any(
            event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "completed-result-cache"
            and event.get("cache_outcome") == "hit"
            for event in events
        )
        assert all(
            event.get("phase") != "modwire-code-map"
            for event in events
            if event.get("event") == "project_health_phase_terminal"
        )

    @pytest.mark.django_db
    def test_repeated_health_reuses_warm_execution_and_observes_source_changes(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        python_project(tmp_path)
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
        healthy = client.get(path)
        (tmp_path / "app.py").write_text(
            "class ExampleApplication:\n    pass\n\nclass ExampleHandler:\n    pass\n",
            encoding="utf-8",
        )
        changed = client.get(path)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]
        terminal_events = [event for event in events if event.get("event") == "project_health_terminal"]
        changed_run_id = terminal_events[-1]["run_id"]
        changed_worker_events = [
            event["event"]
            for event in events
            if event.get("run_id") == changed_run_id
            and event.get("event") in {"project_health_worker_started", "project_health_worker_reused"}
        ]

        assert healthy.status_code == 200
        assert healthy.json()["healthy"] is True
        assert changed.status_code == 200
        assert changed.json()["healthy"] is False
        assert "max_classes_per_file" in {finding["rule"] for finding in changed.json()["failures"]}
        assert changed_worker_events == ["project_health_worker_reused"]

    @pytest.mark.health_serial
    @pytest.mark.django_db
    def test_health_cold_execution_is_stable_across_five_independent_projects(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        record_property: Callable[[str, object], None],
    ) -> None:
        responses = []
        durations = []
        caplog.clear()
        for index in range(5):
            root = tmp_path / str(index)
            root.mkdir()
            python_project(root)
            distinguish_project_source(root, "ColdApplication")
            resolution = client.post(
                "/api/projects",
                data=registration(discover(client, root), dependencies),
                content_type="application/json",
            ).json()
            accept_health_architecture(client, root, resolution)
            project_id = resolution["project"]["id"]
            workspace_id = resolution["workspace"]["id"]
            path = f"/api/projects/{project_id}/workspaces/{workspace_id}/health-violations"
            started = monotonic()
            responses.append(client.get(path))
            durations.append(monotonic() - started)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]
        completed_run_ids = {
            event["run_id"]
            for event in events
            if event.get("event") == "project_health_terminal" and event.get("outcome") == "completed"
        }
        record_property("cold_durations_seconds", ",".join(str(duration) for duration in durations))
        record_property("cold_max_seconds", max(durations))

        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["healthy"] is True for response in responses)
        assert all(response.json()["failures"] == [] for response in responses)
        assert len({tuple(report["id"] for report in response.json()["reports"]) for response in responses}) == 1
        assert max(durations) < 5
        assert len(completed_run_ids) == 5
        assert all(
            any(
                event.get("run_id") == run_id
                and event.get("event") == "project_health_phase_terminal"
                and event.get("phase") == "completed-result-cache"
                and event.get("cache_outcome") == "miss"
                for event in events
            )
            for run_id in completed_run_ids
        )
        assert all(
            sum(
                event.get("run_id") == run_id
                and event.get("event") == "project_health_phase_terminal"
                and event.get("phase") == "modwire-code-map"
                for event in events
            )
            == 1
            for run_id in completed_run_ids
        )

    @pytest.mark.health_serial
    @pytest.mark.django_db
    def test_health_warm_execution_is_stable_across_twenty_requests(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        record_property: Callable[[str, object], None],
    ) -> None:
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "WarmApplication")
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )
        baseline = client.get(path)

        caplog.clear()
        responses = []
        durations = []
        for _ in range(20):
            started = monotonic()
            responses.append(client.get(path))
            durations.append(monotonic() - started)
        ordered_durations = sorted(durations)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]
        completed_run_ids = {
            event["run_id"]
            for event in events
            if event.get("event") == "project_health_terminal" and event.get("outcome") == "completed"
        }
        contract_events = [
            event for event in events if event.get("event") == "project_health_architecture_contract_cache"
        ]
        record_property("warm_durations_seconds", ",".join(str(duration) for duration in ordered_durations))
        record_property("warm_p95_seconds", ordered_durations[18])
        record_property("warm_max_seconds", max(ordered_durations))

        assert baseline.status_code == 200, baseline.json()
        assert all(response.status_code == 200 for response in responses)
        assert all(response.json() == baseline.json() for response in responses)
        assert len(contract_events) == 20
        assert {event["resolution_outcome"] for event in contract_events} == {"reused"}
        assert {event["lookup_outcome"] for event in contract_events} == {"hit"}
        assert {event["compilation_duration_ns"] for event in contract_events} == {0}
        assert len({event["cache_identity"] for event in contract_events}) == 1
        assert len({event["manifest_digest"] for event in contract_events}) == 1
        assert ordered_durations[18] < 1
        assert max(ordered_durations) < 5
        assert len(completed_run_ids) == 20
        assert all(
            any(
                event.get("run_id") == run_id
                and event.get("event") == "project_health_phase_terminal"
                and event.get("phase") == "completed-result-cache"
                and event.get("cache_outcome") == "hit"
                for event in events
            )
            for run_id in completed_run_ids
        )
        assert all(
            event.get("phase") != "modwire-code-map"
            for event in events
            if event.get("event") == "project_health_phase_terminal"
        )
