from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestOperatingContractAttacks:
    @pytest.mark.django_db
    def test_rejected_operating_contract_revision_does_not_consume_a_version_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
    ) -> None:
        contract = client.post(
            "/api/projects/operating-contracts",
            data={
                "title": "Attacked operating contract",
                "authority": "example:attacked-operating-contract",
                "provenance": "verification",
            },
            content_type="application/json",
        ).json()
        url = f"/api/projects/operating-contracts/{contract['id']}/revisions"
        payload = {
            "record_ids": [dependencies["record_id"]],
            "references": [
                {
                    "kind": "policy",
                    "id": "example-policy",
                    "authority": "example:policy",
                    "revision": "1",
                    "unexpected": True,
                }
            ],
        }

        rejected = client.post(url, data=payload, content_type="application/json")

        assert rejected.status_code == 422
        assert client.get(f"{url}/1").status_code == 404

        del payload["references"][0]["unexpected"]
        recovered = client.post(url, data=payload, content_type="application/json")

        assert recovered.status_code == 201
        assert recovered.json()["version"] == 1
        assert client.get(f"{url}/1").json() == recovered.json()


class TestOperatingContractInvariants:
    @pytest.mark.django_db
    def test_protects_guidance_published_in_an_operating_contract(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        approve_operation,
    ) -> None:
        python_project(tmp_path)
        client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        )
        deleted = client.delete(f"/api/records/{dependencies['record_id']}")
        approve_operation(client, deleted)
        deleted = client.delete(f"/api/records/{dependencies['record_id']}")

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )

        assert deleted.status_code == 422
        assert deleted.json() == {"detail": "A record published in an operating contract cannot be deleted."}
        assert response.status_code == 200
        assert response.json()["readiness"] == "ready"
        assert response.json()["receipt"]["diagnostics"] == []

    @pytest.mark.django_db
    def test_marks_stale_guidance_revision_incomplete(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        )
        revised = client.put(
            f"/api/records/categories/{dependencies['category_id']}/content-schema",
            data={"content_schema": {"type": "object", "required": ["summary"]}},
            content_type="application/json",
        )

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )

        assert revised.status_code == 200
        assert response.status_code == 200
        assert response.json()["readiness"] == "incomplete"
        assert response.json()["guidance"][0]["schema_revision"] == 1
        assert response.json()["guidance"][0]["current_schema_revision"] == 2
        assert response.json()["receipt"]["diagnostics"] == [
            {
                "code": "guidance_revision_stale",
                "message": "Bound guidance uses an obsolete category schema revision. Review and republish it.",
                "guidance_ids": [dependencies["record_id"]],
            }
        ]

    @pytest.mark.django_db
    def test_marks_changed_published_guidance_incomplete(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        second = client.post(
            "/api/records",
            data={
                "title": "Additional project context",
                "content": {},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        ).json()
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] = [dependencies["record_id"], second["id"]]
        client.post("/api/projects", data=payload, content_type="application/json")
        changed = client.put(
            f"/api/records/{second['id']}",
            data={
                "title": "Changed project context",
                "content": {},
                "category_id": dependencies["category_id"],
                "tag_ids": [dependencies["tag_id"]],
                "resources": [],
            },
            content_type="application/json",
        )

        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )

        assert changed.status_code == 200
        assert response.status_code == 200
        assert response.json()["readiness"] == "incomplete"
        assert response.json()["receipt"]["diagnostics"] == [
            {
                "code": "guidance_revision_changed",
                "message": "Published operating-contract guidance has changed. Publish a new contract revision.",
                "guidance_ids": [second["id"]],
            }
        ]


class TestOperatingContractHappyPaths:
    @pytest.mark.django_db
    def test_publishes_and_binds_versioned_operating_contract(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        contract_response = client.post(
            "/api/projects/operating-contracts",
            data={
                "title": "Example Python delivery contract",
                "authority": "example:engineering:python-delivery",
                "provenance": "example-repository",
            },
            content_type="application/json",
        )
        assert contract_response.status_code == 201
        contract = contract_response.json()

        first_response = client.post(
            f"/api/projects/operating-contracts/{contract['id']}/revisions",
            data={
                "record_ids": [dependencies["record_id"]],
                "references": [
                    {
                        "kind": "policy",
                        "id": "example-python-policy",
                        "authority": "example:policy:python",
                        "revision": "3",
                    }
                ],
            },
            content_type="application/json",
        )
        assert first_response.status_code == 201
        first = first_response.json()
        assert first["version"] == 1
        assert [reference["kind"] for reference in first["references"]] == ["guidance", "policy"]

        second_response = client.post(
            f"/api/projects/operating-contracts/{contract['id']}/revisions",
            data={
                "record_ids": [dependencies["record_id"]],
                "references": [
                    {
                        "kind": "architecture",
                        "id": "example-python-architecture",
                        "authority": "example:architecture:python",
                        "revision": "5",
                    }
                ],
            },
            content_type="application/json",
        )
        assert second_response.status_code == 201
        assert second_response.json()["version"] == 2
        assert client.get(f"/api/projects/operating-contracts/{contract['id']}/revisions/1").json() == first

        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        payload["record_ids"] = []
        project_response = client.post("/api/projects", data=payload, content_type="application/json")
        assert project_response.status_code == 201
        project = project_response.json()["project"]

        unconfigured = client.get(f"/api/projects/{project['id']}/operating-contract-binding")
        assert unconfigured.status_code == 409
        assert unconfigured.json() == {"state": "unconfigured", "project_id": project["id"]}
        context = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": "Change project source safely"},
            content_type="application/json",
        )
        assert context.status_code == 200
        assert context.json()["readiness"] == "incomplete"
        assert context.json()["receipt"]["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"

        binding_data = {
            "contract_id": contract["id"],
            "version": 1,
            "update_policy": "pinned",
        }
        bound = client.post(
            f"/api/projects/{project['id']}/operating-contract-bindings",
            data=binding_data,
            content_type="application/json",
        )
        assert bound.status_code == 201
        assert bound.json()["effective_revision"]["version"] == 1
        duplicate = client.post(
            f"/api/projects/{project['id']}/operating-contract-bindings",
            data={**binding_data, "version": 2},
            content_type="application/json",
        )
        assert duplicate.status_code == 422

        replaced = client.put(
            f"/api/projects/{project['id']}/operating-contract-binding",
            data={**binding_data, "update_policy": "follow-latest"},
            content_type="application/json",
        )
        assert replaced.status_code == 200
        assert replaced.json()["bound_revision"] == 1
        assert replaced.json()["effective_revision"]["version"] == 2
