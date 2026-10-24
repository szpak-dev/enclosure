from pathlib import Path

import pytest
from django.test import Client
from django.test.utils import override_settings

from ...support import (
    accept_health_architecture,
    discover,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthGuidanceAttacks:
    @pytest.mark.django_db
    def test_health_reports_conflicting_guidance_authority(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        first = client.put(
            f"/api/records/{dependencies['record_id']}",
            data={
                "title": "Project context",
                "content": {"authority": "project-policy"},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        second = client.post(
            "/api/records",
            data={
                "title": "Conflicting project context",
                "content": {"authority": "project-policy"},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] = [first["id"], second["id"]]
        registered = client.post("/api/projects", data=payload, content_type="application/json")
        assert registered.status_code == 201
        accept_health_architecture(client, tmp_path, registered.json())

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )
        resolution = client.post(
            "/api/projects/workspace-resolutions",
            data={"root": str(tmp_path)},
            content_type="application/json",
        ).json()
        project = resolution["project"]
        workspace = resolution["workspace"]
        health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

        assert response.status_code == 200
        assert response.json()["readiness"] == "conflicted"
        assert response.json()["receipt"]["diagnostics"] == [
            {
                "code": "guidance_authority_conflict",
                "message": (
                    "Multiple bound guidance records claim authority 'project-policy'. Bind one effective source."
                ),
                "guidance_ids": sorted([first["id"], second["id"]]),
            }
        ]
        assert health.json()["healthy"] is False
        assert [finding["rule"] for finding in health.json()["failures"]] == ["authority-conflict"]

    @pytest.mark.django_db
    def test_health_reports_malformed_guidance_graph_and_blocks_ready_context(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        supplemental = client.post(
            "/api/records",
            data={
                "title": "Python refinement",
                "content": {"authority": "unrelated:python", "guidance": ["Keep typing strict."]},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        outside = client.post(
            "/api/records",
            data={
                "title": "Outside guidance",
                "content": {"guidance": ["This record is not effective for the project."]},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        project = resolution["project"]
        workspace = resolution["workspace"]
        scoped = client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": [supplemental["id"]]},
            content_type="application/json",
        )
        relationships = client.put(
            f"/api/projects/{project['id']}/guidance-relationships",
            data={
                "relationships": [
                    {
                        "source_record_id": dependencies["record_id"],
                        "target_record_id": supplemental["id"],
                        "kind": "refinement",
                    },
                    {
                        "source_record_id": supplemental["id"],
                        "target_record_id": dependencies["record_id"],
                        "kind": "prerequisite",
                    },
                    {
                        "source_record_id": dependencies["record_id"],
                        "target_record_id": outside["id"],
                        "kind": "containment",
                    },
                ]
            },
            content_type="application/json",
        )

        health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
        context = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change Python typing"},
            content_type="application/json",
        )

        assert scoped.status_code == 200
        assert relationships.status_code == 200
        assert all(relationship["id"] for relationship in relationships.json())
        assert {relationship["project_id"] for relationship in relationships.json()} == {project["id"]}
        assert (
            client.get(f"/api/projects/{project['id']}/guidance-relationships").json()["items"] == relationships.json()
        )
        assert health.status_code == 200
        assert health.json()["healthy"] is False
        rules = {finding["rule"] for finding in health.json()["failures"]}
        assert {
            "ambiguous-entry-point",
            "dangling-relationship",
            "guidance-cycle",
            "invalid-refinement",
        } <= rules
        assert all(finding["related_ids"] for finding in health.json()["failures"])
        assert all(finding["remediation"] for finding in health.json()["failures"])
        assert context.status_code == 200
        assert context.json()["readiness"] == "incomplete"
        assert "guidance-cycle" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}

    @override_settings(RECORDS_EMBEDDINGS_ENABLED=False)
    @pytest.mark.django_db
    def test_workspace_context_reports_individually_oversized_applicable_guidance(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        optional = client.post(
            "/api/records",
            data={
                "title": "Example oversized guidance",
                "content": {
                    "summary": "x" * 5000,
                    "applies_when": ["example budget attack"],
                    "guidance": ["Keep this record whole."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        project = resolution["project"]
        client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": [optional["id"]]},
            content_type="application/json",
        )

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Example budget attack"},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["readiness"] == "ready"
        assert [guidance["id"] for guidance in response.json()["guidance"]] == [dependencies["record_id"]]
        assert response.json()["receipt"]["budget"] == {
            "used_optional_characters": 0,
            "optional_character_limit": 4096,
        }
        assert response.json()["receipt"]["omissions"] == [
            {
                "code": "optional-budget-exhausted",
                "guidance_ids": [optional["id"]],
                "message": "Supplemental guidance was omitted because the workspace-context budget was exhausted.",
            }
        ]
        assert response.json()["receipt"]["stop_condition"] == "resolve-context-gaps"

    @pytest.mark.django_db
    def test_health_blocks_oversized_required_guidance(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        client.put(
            f"/api/records/{dependencies['record_id']}",
            data={
                "title": "Project context",
                "content": {"guidance": ["x" * 9000]},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        project = resolution["project"]
        workspace = resolution["workspace"]

        health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
        context = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )

        assert health.json()["healthy"] is False
        assert [finding["rule"] for finding in health.json()["failures"]] == ["guidance-oversized"]
        assert context.json()["readiness"] == "incomplete"
        assert "guidance-oversized" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}


class TestHealthGuidanceInvariants:
    @override_settings(RECORDS_EMBEDDINGS_ENABLED=False)
    @pytest.mark.django_db
    def test_health_ignores_unselected_optional_catalogue_size(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        selected = client.post(
            "/api/records",
            data={
                "title": "Example selected guidance",
                "content": {
                    "summary": "s" * 500,
                    "applies_when": ["example selected task"],
                    "guidance": ["Select this record."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        unrelated = client.post(
            "/api/records",
            data={
                "title": "Example unrelated guidance",
                "content": {
                    "summary": "u" * 5000,
                    "applies_when": ["example unrelated task"],
                    "guidance": ["Do not select this record."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        project = resolution["project"]
        workspace = resolution["workspace"]
        client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": [selected["id"], unrelated["id"]]},
            content_type="application/json",
        )

        context = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Example selected task"},
            content_type="application/json",
        )
        health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

        assert context.status_code == 200
        assert [guidance["id"] for guidance in context.json()["guidance"]] == [
            dependencies["record_id"],
            selected["id"],
        ]
        assert context.json()["receipt"]["coverage"]["status"] == "complete"
        assert context.json()["receipt"]["omissions"] == []
        assert health.status_code == 200
        assert health.json()["healthy"] is True
        assert health.json()["failures"] == []
        assert {finding["rule"] for finding in health.json()["advisories"]} == {"unreachable-guidance"}
