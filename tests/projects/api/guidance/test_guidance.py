from pathlib import Path

import pytest
from django.test import Client
from django.test.utils import override_settings

from ..support import (
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestGuidanceAttacks:
    @pytest.mark.django_db
    def test_rejected_guidance_relationship_replacement_preserves_graph_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        project = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()["project"]
        url = f"/api/projects/{project['id']}/guidance-relationships"
        relationship = {
            "source_record_id": dependencies["record_id"],
            "target_record_id": dependencies["record_id"],
            "kind": "containment",
            "unexpected": True,
        }

        rejected = client.put(
            url,
            data={"relationships": [relationship]},
            content_type="application/json",
        )

        assert rejected.status_code == 422
        assert client.get(url).json()["items"] == []

        del relationship["unexpected"]
        recovered = client.put(
            url,
            data={"relationships": [relationship]},
            content_type="application/json",
        )

        assert recovered.status_code == 200
        assert [{key: item[key] for key in relationship} for item in recovered.json()] == [relationship]


class TestGuidanceHappyPaths:
    @pytest.mark.django_db
    def test_routes_scoped_guidance_for_representative_tasks(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        database = client.post(
            "/api/records",
            data={
                "title": "Database delivery",
                "content": {
                    "summary": "Safely deliver database changes.",
                    "applies_when": ["database migration"],
                    "guidance": ["Prepare a rollback before applying a migration."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [
                    {
                        "path": "database.md",
                        "language": "markdown",
                        "content": "database migration rollback " * 20,
                    }
                ],
            },
            content_type="application/json",
        )
        python = client.post(
            "/api/records",
            data={
                "title": "Python typing",
                "content": {
                    "summary": "Keep Python typing strict.",
                    "applies_when": ["python typing"],
                    "guidance": ["Keep public annotations precise."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [
                    {
                        "path": "typing.md",
                        "language": "markdown",
                        "content": "python typing annotations",
                    }
                ],
            },
            content_type="application/json",
        )
        universal = client.post(
            "/api/records",
            data={
                "title": "Database migration rollback",
                "content": {
                    "summary": "Database migration rollback.",
                    "guidance": ["Review the completed change."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        unscoped = client.post(
            "/api/records",
            data={
                "title": "Unscoped database policy",
                "content": {
                    "summary": "Belongs to a different project.",
                    "applies_when": ["database migration"],
                    "guidance": ["This guidance must not leak across projects."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        assert {database.status_code, python.status_code, universal.status_code, unscoped.status_code} == {201}

        python_project(tmp_path)
        project = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()["project"]
        replaced = client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": [universal.json()["id"], database.json()["id"], python.json()["id"]]},
            content_type="application/json",
        )

        assert replaced.status_code == 200
        assert [scope["record_id"] for scope in replaced.json()] == [
            universal.json()["id"],
            database.json()["id"],
            python.json()["id"],
        ]
        assert [scope["position"] for scope in replaced.json()] == [1, 2, 3]
        assert client.get(f"/api/projects/{project['id']}/guidance-scopes").json()["items"] == replaced.json()

        corpus = (
            ("database migration rollback", database.json()["id"]),
            ("python typing annotations", python.json()["id"]),
        )
        for task, expected_id in corpus:
            response = client.post(
                "/api/projects/workspace-contexts",
                data={"root": str(tmp_path), "task": task},
                content_type="application/json",
            )

            assert response.status_code == 200
            guidance_ids = [guidance["id"] for guidance in response.json()["guidance"]]
            assert guidance_ids == [dependencies["record_id"], expected_id, universal.json()["id"]]
            assert unscoped.json()["id"] not in guidance_ids
            assert [item["reason"] for item in response.json()["receipt"]["items"]] == [
                "operating-contract",
                "task-applicable",
                "project-default",
            ]

    @override_settings(RECORDS_EMBEDDINGS_ENABLED=False)
    @pytest.mark.django_db
    def test_routes_optional_guidance_by_fallback_order_within_budget(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        first = client.post(
            "/api/records",
            data={
                "title": "First fallback",
                "content": {
                    "summary": "a" * 1800,
                    "guidance": ["Keep this complete."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        second = client.post(
            "/api/records",
            data={
                "title": "Second fallback",
                "content": {
                    "summary": "b" * 3000,
                    "guidance": ["This whole record exceeds the remaining budget."],
                },
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )
        assert first.status_code == 201
        assert second.status_code == 201

        python_project(tmp_path)
        project = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()["project"]
        scoped = client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": [first.json()["id"], second.json()["id"]]},
            content_type="application/json",
        )
        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Any task without ranking support"},
            content_type="application/json",
        )

        assert scoped.status_code == 200
        assert response.status_code == 200
        assert [guidance["id"] for guidance in response.json()["guidance"]] == [
            dependencies["record_id"],
            first.json()["id"],
        ]
        assert response.json()["guidance"][1]["summary"] == "a" * 1800
        assert response.json()["receipt"]["coverage"] == {
            "status": "partial",
            "selected_count": 2,
            "omitted_count": 1,
            "diagnostic_count": 0,
        }
        assert response.json()["receipt"]["omissions"] == [
            {
                "code": "optional-budget-exhausted",
                "guidance_ids": [second.json()["id"]],
                "message": "Supplemental guidance was omitted because the workspace-context budget was exhausted.",
            }
        ]
        assert response.json()["receipt"]["stop_condition"] == "resolve-context-gaps"
