import json
from hashlib import sha256
from pathlib import Path

import pytest
from django.test import Client
from modwire.application import ModwireApplication, ScanPolicy

from ...support import (
    ArchitectureContractFixture,
    create_architecture_contract_fixture,
    discover,
    implementation_document,
    python_project,
    registration,
)

pytestmark = pytest.mark.django_db


class TestArchitectureComparisonAttacks:
    @pytest.mark.django_db
    def test_comparison_rejects_a_tampered_modwire_document(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path)
        document["digest"] = "0" * 64

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 422, response.json()
        assert "digest does not match its payload" in response.json()["detail"]

    @pytest.mark.django_db
    def test_comparison_rejects_multiple_parameter_type_annotations_as_a_mismatch(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path)
        payload = json.loads(str(document["payload"]))
        parameter_annotation = next(
            annotation for annotation in payload["annotations"] if annotation["role"] == "parameter_type"
        )
        payload["annotations"].append(parameter_annotation | {"expression": "int"})
        payload["annotations"].sort(
            key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        )
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        document["payload"] = canonical
        document["digest"] = sha256(canonical.encode("utf-8")).hexdigest()

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        parameter_failures = [
            result
            for result in comparison["results"]
            if result["assertion_kind"] == "member"
            and result["state"] == "fail"
            and result["expected"]["fields"]["name"] == "execute"
        ]
        assert comparison["conclusion"] == "does_not_conform"
        assert [result["kind"] for result in parameter_failures] == ["mismatched"], comparison
        assert "owner_id" not in parameter_failures[0]["expected"]["fields"]
        assert "owner_id" not in parameter_failures[0]["observed"][0]["fields"]

    @pytest.mark.django_db
    def test_public_comparison_reports_missing_member_from_complete_inventory(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path, include_execute=False)

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        missing = [
            result
            for result in comparison["results"]
            if result["assertion_kind"] == "member" and result["state"] == "fail" and result["kind"] == "missing"
        ]
        assert comparison["conclusion"] == "does_not_conform"
        assert comparison["failed"] == 1
        assert comparison["unverified"] == 0
        assert len(missing) == 1

    @pytest.mark.django_db
    def test_public_comparison_reports_language_neutral_entity_field_drift(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path, "models.IntegerField()")

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        failures = [
            result
            for result in comparison["results"]
            if result["assertion_kind"] == "entity_field" and result["state"] == "fail"
        ]
        assert comparison["conclusion"] == "does_not_conform"
        assert len(failures) == 1, comparison
        assert failures[0]["owner"] == "implementation"
        assert failures[0]["expected"]["fields"]["type"]["name"] == "string"
        assert failures[0]["observed"][0]["fields"]["type"]["name"] == "int"
        assert "IntegerField" not in json.dumps(comparison)


class TestArchitectureComparisonInvariants:
    @pytest.mark.django_db
    def test_public_comparison_excludes_python_annotated_metadata_from_parameter_type(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(
            tmp_path,
            request_annotation="typing.Annotated[str, object()]",
        )

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        assert comparison["conclusion"] == "conforms", comparison
        assert comparison["failed"] == 0
        assert comparison["unverified"] == 0
        assert all(result["state"] == "pass" for result in comparison["results"])

    @pytest.mark.django_db
    def test_public_comparison_prefers_exact_classifier_reference_over_duplicate_name(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path, duplicate_service_name=True)

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        assert comparison["conclusion"] == "conforms", comparison
        assert comparison["failed"] == 0
        assert comparison["unverified"] == 0

    @pytest.mark.django_db
    def test_public_comparison_normalizes_python_abc_strategy_realization(
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
        )
        assert registered.status_code == 201, registered.json()
        diagram_set = client.post(
            "/api/diagram-sets",
            data={"title": "Relationship architecture", "description": "Exact relationship realization."},
            content_type="application/json",
        )
        assert diagram_set.status_code == 201, diagram_set.json()
        fixture = ArchitectureContractFixture(client, registered.json()["project"]["id"], diagram_set.json()["id"])
        source = tmp_path / "src" / "example"
        source.mkdir(parents=True)
        (source / "base.py").write_text(
            "from abc import ABC, abstractmethod\n\n"
            "class ExampleBase(ABC):\n"
            "    @abstractmethod\n"
            "    def execute(self) -> None:\n"
            "        raise NotImplementedError\n",
            encoding="utf-8",
        )
        (source / "service.py").write_text(
            "from .base import ExampleBase\n\n"
            "class ExampleService(ExampleBase):\n"
            "    def execute(self) -> None:\n"
            "        return None\n",
            encoding="utf-8",
        )
        (source / "models.py").write_text(
            "from django.db import models\n\n"
            "class ExampleRecordModel(models.Model):\n"
            "    id = models.UUIDField(primary_key=True)\n"
            "    name = models.CharField(max_length=120)\n",
            encoding="utf-8",
        )
        tree = fixture.create_diagram_batch(
            "Relationship structure",
            "treeView-beta",
            [
                {"operation": "add_directory", "arguments": {"id": "source", "label": "src"}},
                {"operation": "add_directory", "arguments": {"id": "example", "label": "example"}},
                {"operation": "add_file", "arguments": {"id": "base", "label": "base.py"}},
                {"operation": "add_file", "arguments": {"id": "service", "label": "service.py"}},
                {"operation": "add_file", "arguments": {"id": "models", "label": "models.py"}},
                {
                    "operation": "add_branch",
                    "arguments": {"id": "source-example", "parent_id": "source", "child_id": "example"},
                },
                {
                    "operation": "add_branch",
                    "arguments": {"id": "example-base", "parent_id": "example", "child_id": "base"},
                },
                {
                    "operation": "add_branch",
                    "arguments": {"id": "example-service", "parent_id": "example", "child_id": "service"},
                },
                {
                    "operation": "add_branch",
                    "arguments": {"id": "example-models", "parent_id": "example", "child_id": "models"},
                },
            ],
        )
        base_id = "src/example/base.py::class:src/example/base.ExampleBase"
        service_id = "src/example/service.py::class:src/example/service.ExampleService"
        uml = fixture.create_diagram_batch(
            "Relationship services",
            "classDiagram",
            [
                {
                    "operation": "add_class",
                    "arguments": {"id": base_id, "label": "ExampleBase", "annotations": ["abstract"]},
                },
                {"operation": "add_class", "arguments": {"id": service_id, "label": "ExampleService"}},
                {
                    "operation": "add_relation",
                    "arguments": {
                        "id": "service-inherits-base",
                        "source_id": service_id,
                        "target_id": base_id,
                        "relation_kind": "realization",
                    },
                },
            ],
        )
        entity = fixture.create_diagram_batch(
            "Relationship entities",
            "erDiagram",
            [
                {"operation": "add_entity", "arguments": {"id": "record", "label": "EXAMPLE_RECORD"}},
                {
                    "operation": "add_attribute",
                    "arguments": {
                        "id": "record-id",
                        "label": "id",
                        "data_type": "string",
                        "entity_id": "record",
                        "keys": ["PK"],
                    },
                },
                {
                    "operation": "add_attribute",
                    "arguments": {
                        "id": "record-name",
                        "label": "name",
                        "data_type": "string",
                        "entity_id": "record",
                    },
                },
            ],
        )
        publication = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications",
            data=fixture.publication_body(tree, uml, entity, coverage="declared"),
            content_type="application/json",
        )
        assert publication.status_code == 201, publication.json()
        application = ModwireApplication.create()
        code_map = application.generate_map("python", str(tmp_path), ScanPolicy(excluded_patterns=("app.py",)))
        document = application.implementation_manifest(code_map, application.implementation_manifest_formats()[0])

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication.json()['id']}/comparisons",
            data={"implementation_document": document.model_dump(mode="json")},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        assert comparison["conclusion"] == "conforms", comparison
        assert comparison["failed"] == 0
        assert comparison["unverified"] == 0

    @pytest.mark.django_db
    def test_closed_comparison_does_not_treat_an_external_import_as_unexpected(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture(coverage="closed")
        document = implementation_document(tmp_path)

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        relationship_failures = [
            result
            for result in comparison["results"]
            if result["assertion_kind"] == "relationship" and result["state"] == "fail"
        ]
        assert relationship_failures == []


class TestArchitectureComparisonHappyPaths:
    @pytest.mark.django_db
    def test_public_comparison_translates_python_callable_signature(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture(value_type={"name": "Callable"})
        document = implementation_document(
            tmp_path,
            value_annotation="typing.Callable[[str], int]",
        )

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        assert comparison["conclusion"] == "conforms", comparison
        assert comparison["failed"] == 0
        assert comparison["unverified"] == 0

    @pytest.mark.django_db
    def test_public_comparison_accepts_language_neutral_entity_contract(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
        publication = fixture.publish_example_architecture()
        document = implementation_document(tmp_path)

        response = client.post(
            f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}/comparisons",
            data={"implementation_document": document},
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        comparison = response.json()
        assert comparison["conclusion"] == "conforms", json.dumps(
            [result for result in comparison["results"] if result["state"] != "pass"],
            indent=2,
        )
        assert comparison["failed"] == 0
        assert comparison["unverified"] == 0
        assert all(result["state"] == "pass" for result in comparison["results"])
        entity_results = [
            result for result in comparison["results"] if result["assertion_kind"] in {"entity", "entity_field"}
        ]
        assert len(entity_results) == 3
