from pathlib import Path
from typing import cast

import pytest
from django.conf import settings
from django.test import Client

from ...support import (
    ArchitectureContractFixture,
    accept_health_architecture,
    discover,
    distinguish_project_source,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthCacheAttacks:
    @pytest.mark.health_serial
    @pytest.mark.django_db(transaction=True)
    def test_health_recovers_from_corrupted_persistent_cache(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
        existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "CorruptCacheApplication")
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
        entries = tuple(
            entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
        )
        completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
        completed_entry.write_bytes(b"{")

        caplog.clear()
        recovered = client.get(path)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]

        assert baseline.status_code == 200, baseline.json()
        assert recovered.status_code == 200, recovered.json()
        assert recovered.json() == baseline.json()
        assert any(
            event.get("event") == "project_health_phase_terminal" and event.get("cache_outcome") == "corrupt"
            for event in events
        )
        assert any(
            event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "final-input-verification"
            and event.get("outcome") == "completed"
            for event in events
        )

    @pytest.mark.health_serial
    @pytest.mark.django_db(transaction=True)
    def test_health_recovers_from_stale_persistent_cache(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
        existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "StaleCacheApplication")
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
        entries = tuple(
            entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
        )
        completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
        other_entry = next(entry for entry in entries if entry.parent.name != "completed-result")
        completed_payload = completed_entry.read_bytes()
        completed_entry.write_bytes(other_entry.read_bytes())
        other_entry.write_bytes(completed_payload)

        caplog.clear()
        recovered = client.get(path)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]

        assert baseline.status_code == 200, baseline.json()
        assert recovered.status_code == 200, recovered.json()
        assert recovered.json() == baseline.json()
        assert any(
            event.get("event") == "project_health_phase_terminal" and event.get("cache_outcome") == "stale"
            for event in events
        )
        assert any(
            event.get("event") == "project_health_phase_terminal"
            and event.get("phase") == "final-input-verification"
            and event.get("outcome") == "completed"
            for event in events
        )

    @pytest.mark.health_serial
    @pytest.mark.django_db(transaction=True)
    def test_health_remains_truthful_when_persistent_cache_is_unavailable(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        cache_directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
        existing_entries = {entry: entry.read_bytes() for entry in cache_directory.rglob("*.json")}
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "UnavailableCacheApplication")
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
        entries = tuple(
            entry for entry in cache_directory.rglob("*.json") if existing_entries.get(entry) != entry.read_bytes()
        )
        completed_entry = next(entry for entry in entries if entry.parent.name == "completed-result")
        completed_payload = completed_entry.read_bytes()
        completed_entry.unlink()
        completed_entry.mkdir()
        caplog.clear()
        try:
            first = client.get(path)
            second = client.get(path)
        finally:
            completed_entry.rmdir()
            completed_entry.write_bytes(completed_payload)
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
        assert baseline.status_code == 200, baseline.json()
        assert first.status_code == 200, first.json()
        assert second.status_code == 200, second.json()
        assert first.json() == baseline.json()
        assert second.json() == baseline.json()
        assert len(completed_run_ids) == 2
        assert all(
            any(
                event.get("run_id") == run_id
                and event.get("event") == "project_health_phase_terminal"
                and event.get("phase") == "cache-persistence"
                and event.get("cache_outcome") == "unavailable"
                for event in events
            )
            for run_id in completed_run_ids
        )
        assert all(
            all(
                event.get("phase") != "modwire-code-map"
                for event in events
                if event.get("run_id") == run_id and event.get("event") == "project_health_phase_terminal"
            )
            for run_id in completed_run_ids
        )


class TestHealthCacheInvariants:
    @pytest.mark.django_db
    def test_health_reuses_exact_stage_caches_after_configuration_change(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "StageCacheApplication")
        payload = registration(discover(client, tmp_path), dependencies)
        resolution = client.post(
            "/api/projects",
            data=payload,
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        caplog.clear()
        cold = client.get(path)
        warm = client.get(path)
        updated = client.put(
            f"/api/projects/{resolution['project']['id']}",
            data={
                "title": resolution["project"]["title"],
                "stack": payload["discovery"]["stack"],
                "boundaries_yaml": payload["boundaries_yaml"],
                "shape_yaml": (
                    "shape:\n"
                    "  realms:\n"
                    "    - name: project\n"
                    '      match: "*"\n'
                    "      shape:\n"
                    "        max_classes_per_file: 2\n"
                ),
                "scaffolding_id": payload["scaffolding_id"],
            },
            content_type="application/json",
        )
        changed = client.get(path)

        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name.startswith("enclosure.projects.services.health")
        ]
        terminal_events = [event for event in events if event.get("event") == "project_health_terminal"]
        cold_run_id, warm_run_id, changed_run_id = (event["run_id"] for event in terminal_events)
        cold_phases = [
            event
            for event in events
            if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == cold_run_id
        ]
        warm_phases = [
            event
            for event in events
            if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == warm_run_id
        ]
        changed_phases = [
            event
            for event in events
            if event.get("event") == "project_health_phase_terminal" and event.get("run_id") == changed_run_id
        ]

        assert cold.status_code == 200, cold.json()
        assert warm.status_code == 200, warm.json()
        assert updated.status_code == 200, updated.json()
        assert changed.status_code == 200, changed.json()
        assert cold.json()["healthy"] is True
        assert warm.json() == cold.json()
        assert changed.json()["healthy"] is True
        assert sum(event["phase"] == "modwire-code-map" for event in cold_phases) == 1
        assert any(
            event["phase"] == "completed-result-cache" and event["cache_outcome"] == "hit" for event in warm_phases
        )
        assert all(event["phase"] != "modwire-code-map" for event in warm_phases)
        assert any(
            event["phase"] == "implementation-manifest"
            and event["outcome"] == "cache-lookup"
            and event["cache_outcome"] == "hit"
            for event in changed_phases
        )
        assert any(
            event["phase"] == "modwire-reports"
            and event["outcome"] == "cache-lookup"
            and event["cache_outcome"] == "miss"
            for event in changed_phases
        )
        assert all(
            any(
                event["phase"] == phase and event["outcome"] == "cache-lookup" and event["cache_outcome"] == "hit"
                for event in changed_phases
            )
            for phase in ("evidence", "realization", "comparison")
        )
        assert any(
            event["phase"] == "attestation" and event["outcome"] == "cache-lookup" and event["cache_outcome"] == "miss"
            for event in changed_phases
        )

    @pytest.mark.django_db
    def test_health_recompiles_only_after_the_accepted_architecture_reference_changes(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        python_project(tmp_path)
        distinguish_project_source(tmp_path, "AcceptedContractCacheApplication")
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
        baseline = client.get(path)
        repeated = client.get(path)
        diagram_set = client.post(
            "/api/diagram-sets",
            data={"title": "Replacement health architecture", "description": "Replacement accepted health contract."},
            content_type="application/json",
        )
        assert diagram_set.status_code == 201, diagram_set.json()
        fixture = ArchitectureContractFixture(
            client,
            resolution["project"]["id"],
            diagram_set.json()["id"],
        )
        publication = fixture.publish_example_architecture()
        fixture.accept_publication(publication)
        changed = client.get(path)
        events = [
            cast(dict[str, object], record.msg)
            for record in caplog.records
            if record.name == "enclosure.projects.services.health.conformance.contract"
            and cast(dict[str, object], record.msg).get("event") == "project_health_architecture_contract_cache"
        ]

        assert baseline.status_code == 200, baseline.json()
        assert repeated.status_code == 200, repeated.json()
        assert changed.status_code == 200, changed.json()
        assert repeated.json() == baseline.json()
        assert changed.json()["healthy"] is True
        assert changed.json()["attestation"]["contract_digest"] != baseline.json()["attestation"]["contract_digest"]
        assert [event["resolution_outcome"] for event in events] == ["compiled", "reused", "compiled"]
        assert [event["lookup_outcome"] for event in events] == ["miss", "hit", "miss"]
        assert [event["store_outcome"] for event in events] == ["stored", "not-applicable", "stored"]
        assert events[0]["cache_identity"] == events[1]["cache_identity"]
        assert events[0]["cache_identity"] != events[2]["cache_identity"]
        assert events[0]["manifest_digest"] == events[1]["manifest_digest"]
        assert events[0]["manifest_digest"] != events[2]["manifest_digest"]
        assert events[0]["compilation_duration_ns"] > 0
        assert events[1]["compilation_duration_ns"] == 0
        assert events[2]["compilation_duration_ns"] > 0
