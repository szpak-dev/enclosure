import json
from hashlib import sha256
from pathlib import Path

import pytest
from django.test import Client

from ...support import (
    ArchitectureContractFixture,
    create_architecture_contract_fixture,
    discover,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestArchitectureContractAttacks:
    @pytest.mark.django_db
    def test_rejects_invalid_project_architecture_contract_members(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        registered = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        diagram_set = client.post(
            "/api/diagram-sets",
            data={"title": "Rejected architecture", "description": "Rejected contract examples."},
            content_type="application/json",
        ).json()
        fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
        tree = fixture.create_diagram(
            "Example structure",
            "treeView-beta",
            "add_directory",
            {"id": "source", "label": "example"},
        )
        uml = fixture.create_diagram(
            "Example services",
            "classDiagram",
            "add_class",
            {"id": "service", "label": "ExampleService"},
        )
        entity = fixture.create_diagram(
            "Example storage",
            "erDiagram",
            "add_entity",
            {"id": "record", "label": "EXAMPLE_RECORD"},
        )
        draft = client.post(
            f"/api/diagram-sets/{fixture.diagram_set_id}/diagrams",
            data={"title": "Draft structure", "kind": "treeView-beta"},
            content_type="application/json",
        ).json()
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications"

        draft_body = fixture.publication_body(draft, uml, entity)
        rejected_draft = client.post(url, data=draft_body, content_type="application/json")
        assert rejected_draft.status_code == 422
        assert rejected_draft.json() == {"detail": f"Architecture diagram {draft['id']!r} is still a draft."}

        unsupported_body = fixture.publication_body(entity, uml, tree)
        rejected_kind = client.post(url, data=unsupported_body, content_type="application/json")
        assert rejected_kind.status_code == 422
        assert "role 'tree' requires 'treeView-beta'" in rejected_kind.json()["detail"]

        stale_body = fixture.publication_body(tree, uml, entity)
        stale_body["units"][0]["diagrams"][0]["expected_revision"] = tree["revision"] + 1
        rejected_stale = client.post(url, data=stale_body, content_type="application/json")
        assert rejected_stale.status_code == 422
        assert rejected_stale.json() == {
            "detail": f"Architecture diagram {tree['id']!r} could not be resolved at revision {tree['revision'] + 1}."
        }

        missing_body = fixture.publication_body(tree, uml, entity)
        missing_body["units"][0]["diagrams"][2]["diagram_id"] = "missing"
        rejected_missing = client.post(url, data=missing_body, content_type="application/json")
        assert rejected_missing.status_code == 422
        assert rejected_missing.json() == {
            "detail": f"Architecture diagram 'missing' could not be resolved at revision {entity['revision']}."
        }

        duplicate_body = fixture.publication_body(tree, uml, entity)
        duplicate_body["units"][0]["diagrams"].append(duplicate_body["units"][0]["diagrams"][1])
        rejected_duplicate = client.post(url, data=duplicate_body, content_type="application/json")
        assert rejected_duplicate.status_code == 422
        assert rejected_duplicate.json() == {
            "detail": f"Architecture diagram {uml['id']!r} is duplicated in the publication."
        }

        exclusion_body = fixture.publication_body(tree, uml, entity)
        exclusion_body["units"][0]["exclusions"] = [{"path": "../generated", "reason": "Outside the unit."}]
        rejected_exclusion = client.post(url, data=exclusion_body, content_type="application/json")
        assert rejected_exclusion.status_code == 422
        assert rejected_exclusion.json() == {
            "detail": "Architecture exclusion '../generated' is not a normalized relative path."
        }

    @pytest.mark.django_db
    def test_rejects_conflicting_architecture_assertions_before_publication(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        registered = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        diagram_set = client.post(
            "/api/diagram-sets",
            data={"title": "Example candidate", "description": "Example candidate contract diagrams."},
            content_type="application/json",
        ).json()
        fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
        tree = fixture.create_diagram(
            "Example structure",
            "treeView-beta",
            "add_directory",
            {"id": "source", "label": "example"},
        )
        uml = fixture.create_diagram_batch(
            "Example services",
            "classDiagram",
            [
                {"operation": "add_class", "arguments": {"id": "source", "label": "ExampleSource"}},
                {"operation": "add_class", "arguments": {"id": "target", "label": "ExampleTarget"}},
                {
                    "operation": "add_relation",
                    "arguments": {
                        "id": "r1",
                        "source_id": "source",
                        "target_id": "target",
                        "relation_kind": "dependency",
                    },
                },
            ],
        )
        entity = fixture.create_diagram_batch(
            "Example entities",
            "erDiagram",
            [
                {"operation": "add_entity", "arguments": {"id": "source", "label": "EXAMPLE_SOURCE"}},
                {"operation": "add_entity", "arguments": {"id": "target", "label": "EXAMPLE_TARGET"}},
                {
                    "operation": "add_relationship",
                    "arguments": {
                        "id": "r1",
                        "source_id": "source",
                        "target_id": "target",
                        "label": "example relation",
                    },
                },
            ],
        )
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications"
        conflicting = client.post(
            url,
            data=fixture.publication_body(tree, uml, entity),
            content_type="application/json",
        )

        assert conflicting.status_code == 422
        assert conflicting.json() == {
            "detail": "Architecture assertion identity 'relationship:r1' has conflicting declarations."
        }

        valid_body = fixture.publication_body(tree, uml, entity)
        valid_body["units"][0]["diagrams"] = valid_body["units"][0]["diagrams"][:2]
        accepted = client.post(url, data=valid_body, content_type="application/json")

        assert accepted.status_code == 201, accepted.json()
        assert accepted.json()["version"] == 1

    @pytest.mark.django_db
    def test_rejected_architecture_publication_does_not_consume_a_version_and_recovers(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        tree = fixture.create_diagram(
            "Attacked structure",
            "treeView-beta",
            "add_directory",
            {"id": "source", "label": "example"},
        )
        uml = fixture.create_diagram(
            "Attacked services",
            "classDiagram",
            "add_class",
            {"id": "service", "label": "ExampleService"},
        )
        entity = fixture.create_diagram(
            "Attacked storage",
            "erDiagram",
            "add_entity",
            {"id": "record", "label": "EXAMPLE_RECORD"},
        )
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications"
        payload = fixture.publication_body(tree, uml, entity)
        payload["units"][0]["diagrams"][0]["unexpected"] = True

        rejected = client.post(url, data=payload, content_type="application/json")

        assert rejected.status_code == 422

        del payload["units"][0]["diagrams"][0]["unexpected"]
        recovered = client.post(url, data=payload, content_type="application/json")

        assert recovered.status_code == 201
        assert recovered.json()["version"] == 1


class TestArchitectureContractHappyPaths:
    @pytest.mark.django_db
    def test_publishes_immutable_project_architecture_contract_evidence(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        registered = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        diagram_set = client.post(
            "/api/diagram-sets",
            data={"title": "Example architecture", "description": "Accepted example contract diagrams."},
            content_type="application/json",
        ).json()
        fixture = ArchitectureContractFixture(client, registered["project"]["id"], diagram_set["id"])
        tree = fixture.create_diagram(
            "Example structure",
            "treeView-beta",
            "add_directory",
            {"id": "source", "label": "example"},
        )
        uml = fixture.create_diagram(
            "Example services",
            "classDiagram",
            "add_class",
            {"id": "service", "label": "ExampleService"},
        )
        entity = fixture.create_diagram(
            "Example storage",
            "erDiagram",
            "add_entity",
            {"id": "record", "label": "EXAMPLE_RECORD"},
        )

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications",
            data=fixture.publication_body(tree, uml, entity),
            content_type="application/json",
        )

        assert response.status_code == 201
        publication = response.json()
        openapi = client.get("/api/openapi.json").json()
        assert (
            openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications"]["post"]["operationId"]
            == "publish_project_architecture_contract"
        )
        assert (
            openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications/{publication_id}"]["get"][
                "operationId"
            ]
            == "get_project_architecture_contract"
        )
        assert (
            openapi["paths"]["/api/projects/{project_id}/architecture-contract-publications/{publication_id}/manifest"][
                "get"
            ]["operationId"]
            == "compile_project_architecture_manifest"
        )
        assert (
            openapi["paths"][
                "/api/projects/{project_id}/architecture-contract-publications/{publication_id}/comparisons"
            ]["post"]["operationId"]
            == "compare_project_architecture_manifest"
        )
        assert publication["project_id"] == fixture.project_id
        assert publication["version"] == 1
        assert publication["authority"] == f"project:{fixture.project_id}:architecture-contract"
        assert len(publication["revision"]) == 64
        assert publication["units"][0]["key"] == "application"
        assert publication["units"][0]["source_root"] == "src/example"
        assert publication["units"][0]["coverage"] == "closed"
        assert publication["units"][0]["exclusions"][0]["path"] == "src/example/generated"
        accepted_diagrams = publication["units"][0]["diagrams"]
        assert [(item["role"], item["scope"], item["kind"]) for item in accepted_diagrams] == [
            ("tree", "complete", "treeView-beta"),
            ("uml", "focused", "classDiagram"),
            ("entity", "complete", "erDiagram"),
        ]
        for item in accepted_diagrams:
            canonical = json.dumps(item["snapshot"], ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            assert item["snapshot_digest"] == sha256(canonical.encode("utf-8")).hexdigest()
            assert item["snapshot_version"] >= 1
            assert len(item["registry_fingerprint"]) == 64

        changed = client.post(
            f"/api/diagrams/{uml['id']}/commands",
            data={
                "expected_revision": uml["revision"],
                "operation": "add_class",
                "arguments": {"id": "repository", "label": "ExampleRepository"},
            },
            content_type="application/json",
        )
        assert changed.status_code == 200
        assert changed.json()["revision"] == uml["revision"] + 1

        stored = client.get(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}"
        )
        assert stored.status_code == 200
        assert stored.json() == publication
