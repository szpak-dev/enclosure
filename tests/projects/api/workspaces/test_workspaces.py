from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    BOUNDARIES_YAML,
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestWorkspaceAttacks:
    @pytest.mark.django_db
    def test_rejects_a_workspace_root_already_bound_to_another_project(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        first_root = tmp_path / "first"
        second_root = tmp_path / "second"
        first_root.mkdir()
        second_root.mkdir()
        python_project(first_root)
        python_project(second_root)
        first = client.post(
            "/api/projects",
            data=registration(discover(client, first_root), dependencies),
            content_type="application/json",
        ).json()
        second = client.post(
            "/api/projects",
            data=registration(discover(client, second_root), dependencies),
            content_type="application/json",
        ).json()

        conflict = client.post(
            f"/api/projects/{second['project']['id']}/workspaces",
            data={"root": str(first_root), "architecture_root": str(first_root)},
            content_type="application/json",
        )

        assert first["project"]["id"] != second["project"]["id"]
        assert conflict.status_code == 422
        assert conflict.json() == {"detail": f"Workspace root is already bound: {first_root}"}


class TestWorkspaceInvariants:
    @pytest.mark.django_db
    def test_rebinds_a_moved_workspace_without_changing_project_identity_or_title(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        original = tmp_path / "original-checkout"
        relocated = tmp_path / "relocated-checkout"
        original.mkdir()
        python_project(original)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, original), dependencies),
            content_type="application/json",
        ).json()
        project = resolution["project"]
        workspace = resolution["workspace"]
        original.rename(relocated)

        stale = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/status")
        replaced = client.put(
            f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
            data={
                "root": str(relocated),
                "architecture_root": str(relocated),
                "expected_revision": 1,
            },
            content_type="application/json",
        )
        conflicted = client.put(
            f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
            data={
                "root": str(original),
                "architecture_root": str(original),
                "expected_revision": 1,
            },
            content_type="application/json",
        )
        resolved = client.post(
            "/api/projects/workspace-resolutions",
            data={"root": str(relocated)},
            content_type="application/json",
        )
        context = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(relocated), "task": "Continue after moving the checkout"},
            content_type="application/json",
        )

        assert stale.status_code == 200
        assert stale.json()["state"] == "missing_root"
        assert replaced.status_code == 200
        assert replaced.json() == {
            **workspace,
            "root": str(relocated),
            "architecture_root": str(relocated),
            "revision": 2,
        }
        assert conflicted.status_code == 422
        assert conflicted.json() == {
            "detail": f"Workspace {workspace['id']!r} revision conflict: expected 1, current revision is 2."
        }
        assert resolved.json() == {"project": project, "workspace": replaced.json()}
        assert resolved.json()["project"]["title"] == "original-checkout"
        assert context.status_code == 200
        assert context.json()["project_id"] == project["id"]
        assert context.json()["guidance"][0]["id"] == dependencies["record_id"]

    @pytest.mark.django_db
    def test_reads_revision_pinned_architecture_configuration_content(
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
        project_id = resolution["project"]["id"]
        reference = client.get(f"/api/projects/{project_id}/architecture-configurations").json()["items"][0]

        response = client.get(
            f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
            data={
                "document": "boundaries_yaml",
                "expected_revision": reference["revision"],
                "offset": 0,
                "limit": 12,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "project_id": project_id,
            "configuration_id": reference["id"],
            "revision": reference["revision"],
            "document": "boundaries_yaml",
            "offset": 0,
            "limit": 12,
            "total_characters": len(BOUNDARIES_YAML),
            "content": BOUNDARIES_YAML[:12],
            "has_more": True,
            "next_offset": 12,
        }

        stale = client.get(
            f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
            data={
                "document": "boundaries_yaml",
                "expected_revision": "stale",
                "offset": 0,
                "limit": 12,
            },
        )
        assert stale.status_code == 422
        assert stale.json() == {"detail": "Architecture configuration changed; get it again before reading content."}

        invalid = client.get(
            f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
            data={
                "document": "boundaries_yaml",
                "expected_revision": reference["revision"],
                "offset": -1,
                "limit": 12,
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"][0]["loc"] == ["query", "offset"]
        assert invalid.json()["detail"][0]["ctx"] == {"ge": 0}


class TestWorkspaceHappyPaths:
    @pytest.mark.django_db
    def test_binds_multiple_worktrees_and_uses_the_selected_workspace(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        approve_operation,
    ) -> None:
        main = tmp_path / "main"
        feature = tmp_path / "feature"
        main.mkdir()
        feature.mkdir()
        python_project(main)
        python_project(feature)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, main), dependencies),
            content_type="application/json",
        ).json()
        project = resolution["project"]

        bound = client.post(
            f"/api/projects/{project['id']}/workspaces",
            data={"root": str(feature), "architecture_root": str(feature)},
            content_type="application/json",
        )
        resolved = client.post(
            "/api/projects/workspace-resolutions",
            data={"root": str(feature)},
            content_type="application/json",
        )
        generated = client.post(
            f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}/source-generations",
            data={"destination": "generated", "parameters": {}},
            content_type="application/json",
        )
        workspaces = client.get(f"/api/projects/{project['id']}/workspaces")
        fetched = client.get(f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}")
        deleted = client.delete(
            f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}",
            data={"expected_revision": 1},
            content_type="application/json",
        )
        approve_operation(client, deleted)
        deleted = client.delete(
            f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}",
            data={"expected_revision": 1},
            content_type="application/json",
        )

        assert bound.status_code == 201
        assert bound.json() == {
            "id": bound.json()["id"],
            "project_id": project["id"],
            "root": str(feature),
            "architecture_root": str(feature),
            "revision": 1,
        }
        assert resolved.status_code == 200
        assert resolved.json() == {"project": project, "workspace": bound.json()}
        assert workspaces.json()["items"] == [
            bound.json(),
            resolution["workspace"],
        ]
        assert fetched.json() == bound.json()
        assert generated.status_code == 200
        assert (feature / "generated" / "src" / "package" / "__init__.py").is_file()
        assert not (main / "generated").exists()
        assert deleted.status_code == 204
        assert client.get(f"/api/projects/{project['id']}/workspaces").json()["items"] == [resolution["workspace"]]

    @pytest.mark.django_db
    def test_gets_ready_workspace_context_from_linked_records(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        created = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()["project"]

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )

        context = response.json()

        assert response.status_code == 200
        assert context == {
            "project_id": created["id"],
            "root": str(tmp_path),
            "readiness": "ready",
            "guidance": [
                {
                    "id": dependencies["record_id"],
                    "title": "Project context",
                    "summary": "Project context",
                    "authority": f"record:{dependencies['record_id']}",
                    "revision": context["guidance"][0]["revision"],
                    "schema_revision": 1,
                    "current_schema_revision": 1,
                    "applies_when": [],
                    "guidance": [],
                    "checks": [],
                }
            ],
            "receipt": {
                "authority": {
                    "kind": "project-operating-contract",
                    "id": f"project:{created['id']}:operating-contract",
                    "revision": "1",
                    "provenance": "project-registration",
                },
                "items": [
                    {
                        "record_id": dependencies["record_id"],
                        "title": "Project context",
                        "requirement": "mandatory",
                        "reason": "operating-contract",
                        "explanation": "Required by the active project operating contract.",
                        "authority": f"record:{dependencies['record_id']}",
                        "revision": context["guidance"][0]["revision"],
                        "checks": [],
                    }
                ],
                "required_checks": [],
                "budget": {
                    "used_optional_characters": 0,
                    "optional_character_limit": 4096,
                },
                "coverage": {
                    "status": "complete",
                    "selected_count": 1,
                    "omitted_count": 0,
                    "diagnostic_count": 0,
                },
                "omissions": [],
                "diagnostics": [],
                "stop_condition": "selected-guidance-and-checks",
            },
        }
