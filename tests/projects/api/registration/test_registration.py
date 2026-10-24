from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    BOUNDARIES_YAML,
    COMPLETE_BOUNDARIES_YAML,
    COMPLETE_SHAPE_YAML,
    HEALTHY_SHAPE_YAML,
    UNHEALTHY_SHAPE_YAML,
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestRegistrationAttacks:
    @pytest.mark.django_db
    def test_registration_rejects_invalid_architecture_yaml(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies, shape_yaml="shape: [")

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 422
        assert response.json()["detail"].startswith("Invalid architecture configuration:")

    @pytest.mark.django_db
    def test_get_project_returns_not_found(self, client: Client) -> None:
        response = client.get("/api/projects/missing")

        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found."}

    @pytest.mark.django_db
    def test_update_project_returns_not_found(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)

        response = client.put(
            "/api/projects/missing",
            data={
                "title": "Missing project",
                "stack": discover(client, tmp_path)["stack"],
                "boundaries_yaml": BOUNDARIES_YAML,
                "shape_yaml": HEALTHY_SHAPE_YAML,
                "scaffolding_id": dependencies["scaffolding_id"],
            },
            content_type="application/json",
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found."}

    @pytest.mark.django_db
    def test_registration_rejects_missing_scaffolding(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["scaffolding_id"] = "missing"

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found."}

    @pytest.mark.django_db
    def test_registration_rejects_missing_record(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] = ["missing"]

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 422
        assert response.json() == {"detail": "Operating contract guidance must reference existing records."}

    @pytest.mark.django_db
    def test_registration_rejects_duplicate_record_bindings(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] *= 2

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 422
        assert response.json() == {"detail": "An operating contract revision cannot reference guidance more than once."}

    @pytest.mark.django_db
    def test_registration_rejects_duplicate_project_root(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        created = client.post("/api/projects", data=payload, content_type="application/json")
        assert created.status_code == 201

        duplicate = client.post("/api/projects", data=payload, content_type="application/json")

        assert duplicate.status_code == 422
        assert duplicate.json() == {"detail": f"Workspace root is already bound: {tmp_path}"}

    @pytest.mark.django_db
    def test_failed_registration_does_not_reserve_project_root(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] = [dependencies["record_id"], "missing"]

        failed = client.post("/api/projects", data=payload, content_type="application/json")
        assert failed.status_code == 422

        payload["record_ids"] = [dependencies["record_id"]]
        retried = client.post("/api/projects", data=payload, content_type="application/json")

        assert retried.status_code == 201

    @pytest.mark.django_db
    def test_registration_rejects_nested_unknown_input_before_bootstrap_persistence_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["discovery"]["stack"]["unexpected"] = True

        rejected = client.post("/api/projects", data=payload, content_type="application/json")

        assert rejected.status_code == 422
        assert client.get("/api/projects").json()["items"] == []

        del payload["discovery"]["stack"]["unexpected"]
        recovered = client.post("/api/projects", data=payload, content_type="application/json")

        assert recovered.status_code == 201
        project_id = recovered.json()["project"]["id"]
        binding = client.get(f"/api/projects/{project_id}/operating-contract-binding")
        assert binding.status_code == 200
        assert binding.json()["effective_revision"]["version"] == 1
        assert [reference["id"] for reference in binding.json()["effective_revision"]["references"]] == [
            dependencies["record_id"]
        ]

    @pytest.mark.django_db
    def test_update_rejects_nested_unknown_input_without_changing_project_or_configuration_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        created = client.post("/api/projects", data=payload, content_type="application/json")
        assert created.status_code == 201
        project = created.json()["project"]
        project_url = f"/api/projects/{project['id']}"
        configuration_url = f"{project_url}/architecture-configurations"
        configuration_reference = client.get(configuration_url).json()["items"][0]
        configuration_detail_url = f"{configuration_url}/{configuration_reference['id']}"
        configuration_before = client.get(configuration_detail_url).json()
        update = {
            "title": "Recovered project title",
            "stack": {**payload["discovery"]["stack"], "unexpected": True},
            "boundaries_yaml": payload["boundaries_yaml"],
            "shape_yaml": UNHEALTHY_SHAPE_YAML,
            "scaffolding_id": payload["scaffolding_id"],
        }

        rejected = client.put(project_url, data=update, content_type="application/json")

        assert rejected.status_code == 422
        assert client.get(project_url).json() == project
        assert client.get(configuration_detail_url).json() == configuration_before

        del update["stack"]["unexpected"]
        recovered = client.put(project_url, data=update, content_type="application/json")

        assert recovered.status_code == 200
        assert recovered.json() == {**project, "title": "Recovered project title"}
        assert client.get(configuration_detail_url).json()["shape_yaml"] == UNHEALTHY_SHAPE_YAML


class TestRegistrationHappyPaths:
    @pytest.mark.django_db
    def test_registers_discovered_project(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 201
        assert response.json() == {
            "project": {
                "id": response.json()["project"]["id"],
                "title": tmp_path.name,
                "language_id": "python",
                "language_version": "",
                "package_manager_id": "uv",
                "scaffolding_id": dependencies["scaffolding_id"],
            },
            "workspace": {
                "id": response.json()["workspace"]["id"],
                "project_id": response.json()["project"]["id"],
                "root": str(tmp_path),
                "architecture_root": str(tmp_path),
                "revision": 1,
            },
        }

    @pytest.mark.django_db
    def test_registration_accepts_complete_architecture_configuration(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies, shape_yaml=COMPLETE_SHAPE_YAML)
        payload["boundaries_yaml"] = COMPLETE_BOUNDARIES_YAML

        response = client.post("/api/projects", data=payload, content_type="application/json")

        assert response.status_code == 201

    @pytest.mark.django_db
    def test_updates_registered_project(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        created = client.post("/api/projects", data=payload, content_type="application/json")
        assert created.status_code == 201
        project = created.json()["project"]

        update = {
            "title": "Renamed project",
            "stack": payload["discovery"]["stack"],
            "boundaries_yaml": payload["boundaries_yaml"],
            "shape_yaml": UNHEALTHY_SHAPE_YAML,
            "scaffolding_id": payload["scaffolding_id"],
        }
        updated = client.put(
            f"/api/projects/{project['id']}",
            data=update,
            content_type="application/json",
        )

        assert updated.status_code == 200
        assert updated.json() == {**project, "title": "Renamed project"}
        assert client.get(f"/api/projects/{project['id']}").json() == updated.json()
        configurations = client.get(f"/api/projects/{project['id']}/architecture-configurations")
        assert configurations.status_code == 200
        references = configurations.json()["items"]
        assert len(references) == 1
        assert references[0]["project_id"] == project["id"]
        configuration = client.get(f"/api/projects/{project['id']}/architecture-configurations/{references[0]['id']}")
        assert configuration.status_code == 200
        assert configuration.json() == {
            "id": references[0]["id"],
            "project_id": project["id"],
            "revision": references[0]["revision"],
            "boundaries_yaml": BOUNDARIES_YAML,
            "shape_yaml": UNHEALTHY_SHAPE_YAML,
            "boundaries_document": "boundaries_yaml",
            "shape_document": "shape_yaml",
            "boundaries_total_characters": len(BOUNDARIES_YAML),
            "shape_total_characters": len(UNHEALTHY_SHAPE_YAML),
        }
