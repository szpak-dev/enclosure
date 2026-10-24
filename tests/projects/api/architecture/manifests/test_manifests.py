from pathlib import Path

import pytest
from django.test import Client

from ...support import (
    create_architecture_contract_fixture,
)

pytestmark = pytest.mark.django_db


class TestArchitectureManifestInvariants:
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
