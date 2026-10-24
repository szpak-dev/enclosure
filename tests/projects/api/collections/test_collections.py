from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestProjectCollectionInvariants:
    @pytest.mark.django_db
    def test_project_collections_are_deterministically_paginated(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        projects = []
        for index in range(3):
            root = tmp_path / f"project-{index}"
            root.mkdir()
            python_project(root)
            created = client.post(
                "/api/projects",
                data=registration(discover(client, root), dependencies),
                content_type="application/json",
            )
            assert created.status_code == 201
            projects.append(created.json()["project"])
        project = projects[0]
        for index in range(2):
            root = tmp_path / f"worktree-{index}"
            root.mkdir()
            python_project(root)
            bound = client.post(
                f"/api/projects/{project['id']}/workspaces",
                data={"root": str(root), "architecture_root": str(root)},
                content_type="application/json",
            )
            assert bound.status_code == 201
        records = [dependencies["record_id"]]
        for index in range(3):
            record = client.post(
                "/api/records",
                data={
                    "title": f"Pagination guidance {index}",
                    "content": {},
                    "category_id": dependencies["category_id"],
                    "tag_ids": [dependencies["tag_id"]],
                    "resources": [],
                },
                content_type="application/json",
            )
            assert record.status_code == 201
            records.append(record.json()["id"])
        scopes = client.put(
            f"/api/projects/{project['id']}/guidance-scopes",
            data={"record_ids": records[1:]},
            content_type="application/json",
        )
        relationships = client.put(
            f"/api/projects/{project['id']}/guidance-relationships",
            data={
                "relationships": [
                    {
                        "source_record_id": source,
                        "target_record_id": target,
                        "kind": "containment",
                    }
                    for source, target in zip(records[:3], records[1:], strict=True)
                ]
            },
            content_type="application/json",
        )
        assert scopes.status_code == 200
        assert relationships.status_code == 200

        three_item_paths = (
            "/api/projects",
            f"/api/projects/{project['id']}/workspaces",
            f"/api/projects/{project['id']}/guidance-scopes",
            f"/api/projects/{project['id']}/guidance-relationships",
        )
        for path in three_item_paths:
            first = client.get(path, {"offset": 0, "limit": 1})
            intermediate = client.get(path, {"offset": 1, "limit": 1})
            final = client.get(path, {"offset": 2, "limit": 1})
            empty = client.get(path, {"offset": 3, "limit": 1})

            assert first.status_code == 200
            assert len(first.json()["items"]) == 1
            assert first.json()["has_more"] is True
            assert first.json()["next_offset"] == 1
            assert first.json()["limit"] == 1
            assert intermediate.status_code == 200
            assert len(intermediate.json()["items"]) == 1
            assert intermediate.json()["has_more"] is True
            assert intermediate.json()["next_offset"] == 2
            assert intermediate.json()["limit"] == 1
            assert final.status_code == 200
            assert len(final.json()["items"]) == 1
            assert final.json()["has_more"] is False
            assert final.json()["next_offset"] == 3
            assert final.json()["limit"] == 1
            assert empty.status_code == 200
            assert empty.json() == {
                "items": [],
                "has_more": False,
                "next_offset": 3,
                "limit": 1,
            }

        configuration_path = f"/api/projects/{project['id']}/architecture-configurations"
        configuration = client.get(configuration_path, {"offset": 0, "limit": 1})
        empty_configuration = client.get(configuration_path, {"offset": 1, "limit": 1})

        assert configuration.status_code == 200
        assert len(configuration.json()["items"]) == 1
        assert configuration.json()["has_more"] is False
        assert configuration.json()["next_offset"] == 1
        assert configuration.json()["limit"] == 1
        assert empty_configuration.status_code == 200
        assert empty_configuration.json() == {
            "items": [],
            "has_more": False,
            "next_offset": 1,
            "limit": 1,
        }

    def test_sirenity_owns_project_collection_continuation_links(self) -> None:
        schema = Client().get("/api/openapi.json").json()
        paths = (
            "/api/projects",
            "/api/projects/{project_id}/workspaces",
            "/api/projects/{project_id}/guidance-scopes",
            "/api/projects/{project_id}/guidance-relationships",
            "/api/projects/{project_id}/architecture-configurations",
        )

        for path in paths:
            operation = schema["paths"][path]["get"]
            links = operation["responses"]["200"]["links"]
            assert links["next"]["operationId"] == operation["operationId"]
            assert links["next"]["parameters"] == {
                "offset": "$response.body#/next_offset",
                "limit": "$response.body#/limit",
            }
            if "{project_id}" in path:
                assert links["next"]["x-sirenity"]["sourceInputs"] == {"project_id": "$request.path.project_id"}
            item_links = [link for name, link in links.items() if name != "next"]
            assert item_links
            assert all(link["x-sirenity"]["itemCollection"] == "$response.body#/items" for link in item_links)

    def test_project_bounded_page_schemas_publish_current_limits(self) -> None:
        schema = Client().get("/api/openapi.json").json()
        operations = {
            "/api/projects/{project_id}/architecture-configurations/{configuration_id}/content": {
                "offset": {"minimum": 0},
                "limit": {"minimum": 0},
            },
            "/api/projects/{project_id}/workspaces/{workspace_id}/insights/pages": {
                "offset": {"minimum": 0},
                "limit": {"minimum": 1, "maximum": 25},
            },
            "/api/projects/{project_id}/workspaces/{workspace_id}/health-findings": {
                "offset": {"minimum": 0},
                "limit": {"minimum": 0},
            },
            "/api/projects/{project_id}/workspaces/{workspace_id}/insights/content": {
                "section_offset": {"minimum": 0},
                "item_offset": {"minimum": 0},
                "limit": {"minimum": 0},
            },
        }

        for path, expected_bounds in operations.items():
            parameters = {
                parameter["name"]: parameter["schema"]
                for parameter in schema["paths"][path]["get"]["parameters"]
                if parameter["in"] == "query"
            }
            for name, bounds in expected_bounds.items():
                assert {key: parameters[name][key] for key in bounds} == bounds

    @pytest.mark.django_db
    def test_project_collection_pagination_is_bounded(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        response = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        )
        assert response.status_code == 201
        project_id = response.json()["project"]["id"]
        paths = (
            "/api/projects",
            f"/api/projects/{project_id}/workspaces",
            f"/api/projects/{project_id}/guidance-scopes",
            f"/api/projects/{project_id}/guidance-relationships",
            f"/api/projects/{project_id}/architecture-configurations",
        )

        for path in paths:
            assert client.get(path, {"offset": -1, "limit": 10}).status_code == 422
            assert client.get(path, {"offset": 0, "limit": 101}).status_code == 422


class TestProjectCollectionHappyPaths:
    @pytest.mark.django_db
    def test_lists_and_fetches_registered_projects(
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
        )
        assert created.status_code == 201
        resolution = created.json()
        project = resolution["project"]

        listed = client.get("/api/projects")
        found = client.post(
            "/api/projects/root-search-results",
            data={"root": str(tmp_path)},
            content_type="application/json",
        )
        resolved = client.post(
            "/api/projects/workspace-resolutions",
            data={"root": str(tmp_path)},
            content_type="application/json",
        )
        fetched = client.get(f"/api/projects/{project['id']}")

        assert listed.status_code == 200
        assert listed.json()["items"] == [{"id": project["id"], "title": project["title"]}]
        assert found.status_code == 200
        assert found.json() == project
        assert resolved.status_code == 200
        assert resolved.json() == resolution
        assert fetched.status_code == 200
        assert fetched.json() == project

    def test_siren_root_exposes_projects_collection(self, client: Client) -> None:
        response = client.get("/siren/", headers={"accept": "application/vnd.siren+json"})

        assert response.status_code == 200
        assert {link["href"] for link in response.json()["links"]} >= {
            "http://testserver/siren/projects",
        }
