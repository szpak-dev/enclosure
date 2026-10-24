from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestGenerationAttacks:
    @pytest.mark.django_db
    def test_generation_rejects_rendered_path_collisions_without_filesystem_mutation_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        scaffolding = client.post(
            "/api/scaffoldings",
            data={
                "language_id": "python",
                "name": "Example dynamic paths",
                "description": "Example generated package topology.",
                "spec": {
                    "language": "python",
                    "variables": [
                        {"name": "example_first", "type": "string"},
                        {"name": "example_second", "type": "string"},
                    ],
                    "templates": [
                        {
                            "path": "{{ example_first }}.jinja",
                            "content": "first",
                            "write_mode": "overwrite",
                        },
                        {
                            "path": "{{ example_second }}/child.py.jinja",
                            "content": "second",
                            "write_mode": "overwrite",
                        },
                    ],
                },
            },
            content_type="application/json",
        )
        assert scaffolding.status_code == 201
        project_dependencies = {**dependencies, "scaffolding_id": scaffolding.json()["id"]}
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), project_dependencies),
            content_type="application/json",
        ).json()
        generation_path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations"
        )
        output = tmp_path / "generated"
        output.mkdir()
        sentinel = output / "example-sentinel.txt"
        sentinel.write_text("existing", encoding="utf-8")

        rejected = client.post(
            generation_path,
            data={
                "destination": "generated",
                "parameters": {"example_first": "example", "example_second": "example"},
            },
            content_type="application/json",
        )

        assert rejected.status_code == 422
        assert rejected.json() == {
            "detail": "Rendered scaffolding paths conflict as files and directories: example and example/child.py"
        }
        assert sentinel.read_text(encoding="utf-8") == "existing"
        assert not (output / "example").exists()

        recovered = client.post(
            generation_path,
            data={
                "destination": "generated",
                "parameters": {"example_first": "example.txt", "example_second": "example"},
            },
            content_type="application/json",
        )

        assert recovered.status_code == 200
        assert recovered.json() == {"files": ["generated/example.txt", "generated/example/child.py"]}
        assert (output / "example.txt").read_text(encoding="utf-8") == "first"
        assert (output / "example" / "child.py").read_text(encoding="utf-8") == "second"

    @pytest.mark.django_db
    def test_generation_preflights_a_later_parent_file_before_writing_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        scaffolding = client.post(
            "/api/scaffoldings",
            data={
                "language_id": "python",
                "name": "Example parent conflict",
                "description": "Example parent-file preflight.",
                "spec": {
                    "language": "python",
                    "variables": [],
                    "templates": [
                        {"path": "example-first.txt", "content": "first", "write_mode": "overwrite"},
                        {
                            "path": "example-parent/example-second.txt",
                            "content": "second",
                            "write_mode": "overwrite",
                        },
                    ],
                },
            },
            content_type="application/json",
        )
        assert scaffolding.status_code == 201
        project_dependencies = {**dependencies, "scaffolding_id": scaffolding.json()["id"]}
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), project_dependencies),
            content_type="application/json",
        ).json()
        generation_path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations"
        )
        output = tmp_path / "generated"
        output.mkdir()
        occupied_parent = output / "example-parent"
        occupied_parent.write_text("existing", encoding="utf-8")

        rejected = client.post(
            generation_path,
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert rejected.status_code == 422
        assert rejected.json() == {"detail": "Generation path is occupied by a file: generated/example-parent"}
        assert not (output / "example-first.txt").exists()
        assert occupied_parent.read_text(encoding="utf-8") == "existing"

        occupied_parent.unlink()
        recovered = client.post(
            generation_path,
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert recovered.status_code == 200
        assert recovered.json() == {
            "files": [
                "generated/example-first.txt",
                "generated/example-parent/example-second.txt",
            ]
        }
        assert (output / "example-first.txt").read_text(encoding="utf-8") == "first"
        assert (output / "example-parent" / "example-second.txt").read_text(encoding="utf-8") == "second"

    @pytest.mark.django_db
    def test_generation_preflights_a_later_target_directory_before_writing_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        scaffolding = client.post(
            "/api/scaffoldings",
            data={
                "language_id": "python",
                "name": "Example directory conflict",
                "description": "Example target-directory preflight.",
                "spec": {
                    "language": "python",
                    "variables": [],
                    "templates": [
                        {"path": "example-first.txt", "content": "first", "write_mode": "overwrite"},
                        {"path": "example-target", "content": "second", "write_mode": "overwrite"},
                    ],
                },
            },
            content_type="application/json",
        )
        assert scaffolding.status_code == 201
        project_dependencies = {**dependencies, "scaffolding_id": scaffolding.json()["id"]}
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), project_dependencies),
            content_type="application/json",
        ).json()
        generation_path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations"
        )
        output = tmp_path / "generated"
        occupied_target = output / "example-target"
        occupied_target.mkdir(parents=True)
        marker = occupied_target / "example-marker.txt"
        marker.write_text("existing", encoding="utf-8")

        rejected = client.post(
            generation_path,
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert rejected.status_code == 422
        assert rejected.json() == {
            "detail": "Generation destination is an existing directory: generated/example-target"
        }
        assert not (output / "example-first.txt").exists()
        assert marker.read_text(encoding="utf-8") == "existing"

        marker.unlink()
        occupied_target.rmdir()
        recovered = client.post(
            generation_path,
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert recovered.status_code == 200
        assert recovered.json() == {"files": ["generated/example-first.txt", "generated/example-target"]}
        assert (output / "example-first.txt").read_text(encoding="utf-8") == "first"
        assert occupied_target.read_text(encoding="utf-8") == "second"

    @pytest.mark.django_db
    def test_generation_rejects_destination_outside_project_root(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        outside = tmp_path.parent / f"{tmp_path.name}-outside"

        response = client.post(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
            data={"destination": f"../{outside.name}", "parameters": {}},
            content_type="application/json",
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "Generation destination escapes the project root."}
        assert not outside.exists()


class TestGenerationInvariants:
    @pytest.mark.django_db
    def test_generation_respects_create_if_missing(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        scaffolding = client.get(f"/api/scaffoldings/{dependencies['scaffolding_id']}").json()
        manifest = scaffolding["spec"]["templates"][0]
        content = client.get(
            f"/api/scaffoldings/{dependencies['scaffolding_id']}/template-content",
            data={
                "path": manifest["path"],
                "expected_revision": manifest["revision"],
                "offset": 0,
                "limit": 512,
            },
        )
        assert content.status_code == 200
        update = {
            "language_id": scaffolding["language_id"],
            "name": scaffolding["name"],
            "description": scaffolding["description"],
            "spec": {
                "language": scaffolding["spec"]["language"],
                "variables": scaffolding["spec"]["variables"],
                "templates": [
                    {
                        "path": manifest["path"],
                        "content": content.json()["content"],
                        "write_mode": "create_if_missing",
                    }
                ],
            },
        }
        updated = client.put(
            f"/api/scaffoldings/{dependencies['scaffolding_id']}",
            data=update,
            content_type="application/json",
        )
        assert updated.status_code == 200
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        target = tmp_path / "generated" / "src" / "package" / "__init__.py"
        target.parent.mkdir(parents=True)
        target.write_text("existing", encoding="utf-8")

        response = client.post(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "Destination already contains: generated/src/package/__init__.py"}
        assert target.read_text(encoding="utf-8") == "existing"


class TestGenerationHappyPaths:
    @pytest.mark.django_db
    def test_generates_project_source_from_associated_scaffolding(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        target = tmp_path / "generated" / "src" / "package" / "__init__.py"
        target.parent.mkdir(parents=True)
        target.write_text("existing", encoding="utf-8")

        response = client.post(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json() == {"files": ["generated/src/package/__init__.py"]}
        assert target.read_text(encoding="utf-8") == ""

    @pytest.mark.django_db
    def test_installs_agent_instructions_at_workspace_root(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        target = tmp_path / "AGENTS.md"
        target.write_text("replace me\n", encoding="utf-8")

        response = client.put(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/agent-instructions"
        )

        assert response.status_code == 200
        assert response.json() == {"files": ["AGENTS.md"]}
        assert target.is_file()
        assert not target.is_symlink()
        installed = target.read_text(encoding="utf-8")
        assert "enclosure-mcp.get_workspace_context(root, task)" in installed
        assert "enclosure-mcp.check_project_health" in installed
        assert installed.endswith("\n")
        assert installed.rstrip("\n").count("\n") == 0
