from collections.abc import Callable
from pathlib import Path

import pytest
from django.http import HttpResponseBase
from django.test import Client

from ...support import (
    create_architecture_contract_fixture,
)

pytestmark = pytest.mark.django_db


class TestArchitectureManifestInvariants:
    def test_legacy_archive_rejects_unknown_fields_and_recovers_without_rewriting_evidence(
        self, client: Client, legacy_architecture: Callable[[bool], str]
    ) -> None:
        url = legacy_architecture(True)
        rejected = client.get(f"{url}/manifest")
        assert rejected.status_code == 422

        url = legacy_architecture(False)
        before = client.get(url).json()
        compiled = client.get(f"{url}/manifest")
        assert compiled.status_code == 200, compiled.json()
        assert compiled.json()["units"][0]["assertions"]
        assert client.get(url).json() == before

    def test_manifest_compilation_preserves_published_snapshot_evidence(
        self, client: Client, dependencies: dict[str, str], tmp_path: Path
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}"
        before = client.get(url)

        compiled = client.get(f"{url}/manifest")
        after = client.get(url)

        assert before.status_code == 200
        assert compiled.status_code == 200, compiled.json()
        assert after.status_code == 200
        assert after.json() == before.json()

    def test_archived_manifest_survives_deletion_of_its_source_diagrams(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
        approve_operation: Callable[[Client, HttpResponseBase], None],
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"
        before = client.get(url)
        assert before.status_code == 200, before.json()

        for diagram in publication["units"][0]["diagrams"]:
            approval_required = client.delete(f"/api/diagrams/{diagram['diagram_id']}")
            approve_operation(client, approval_required)
            deleted = client.delete(f"/api/diagrams/{diagram['diagram_id']}")
            assert deleted.status_code == 204

        after = client.get(url)

        assert after.status_code == 200, after.json()
        assert after.json() == before.json()

    @pytest.mark.django_db
    def test_manifest_compilation_keeps_uml_members_separate_from_entity_fields(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture(
            (
                {
                    "operation": "add_attribute",
                    "arguments": {
                        "id": "entity-value",
                        "label": "value",
                        "data_type": "int",
                        "entity_id": "example-record",
                    },
                },
            )
        )

        response = client.get(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"
        )

        assert response.status_code == 200, response.json()
        assertions = response.json()["units"][0]["assertions"]
        assert any(item["kind"] == "member" and item["name"] == "value" for item in assertions)
        assert any(item["kind"] == "entity_field" and item["name"] == "value" for item in assertions)

    @pytest.mark.django_db
    def test_compiled_architecture_manifest_is_stable_at_the_public_gate(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        url = f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"

        first = client.get(url)
        second = client.get(url)

        assert first.status_code == 200, first.json()
        assert second.status_code == 200, second.json()
        assert first.json() == second.json()
        assert len(first.json()["digest"]) == 64

    @pytest.mark.django_db
    def test_compiled_architecture_manifest_preserves_the_complete_attribute_contract(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()

        response = client.get(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/manifest"
        )

        assert response.status_code == 200, response.json()
        attribute = next(
            assertion
            for assertion in response.json()["units"][0]["assertions"]
            if assertion["kind"] == "member" and assertion["name"] == "value"
        )
        assert {
            "name": attribute["name"],
            "type": attribute["type"],
            "visibility": attribute["visibility"],
            "ownership": attribute["ownership"],
        } == {
            "name": "value",
            "type": {"name": "String", "arguments": [], "cardinality": "one"},
            "visibility": "public",
            "ownership": "instance",
        }
