import pytest

from .support import ArchivedArchitectureApplicationFactory

pytestmark = pytest.mark.django_db


class TestArchivedSnapshotContractAttacks:
    def test_rejects_unknown_contract_identity(
        self,
        archived_architecture_application: ArchivedArchitectureApplicationFactory,
    ) -> None:
        architecture = archived_architecture_application.create(7, "0" * 64)

        response = architecture.client.get(architecture.manifest_url)

        assert response.status_code == 422
        assert response.json() == {"detail": "Architecture diagram contract semantics could not be interpreted."}

    def test_rejects_malformed_snapshot_evidence(
        self,
        archived_architecture_application: ArchivedArchitectureApplicationFactory,
    ) -> None:
        architecture = archived_architecture_application.create(
            7,
            "6e19987b9b38c43297098b7acc48149b5d684c055659ba460ae6a6273e6b9c30",
        )
        archived_architecture_application.remove_draft_evidence(architecture)

        response = architecture.client.get(architecture.manifest_url)

        assert response.status_code == 422
        assert response.json() == {"detail": "Architecture diagram contract semantics could not be interpreted."}


class TestArchivedSnapshotContractInvariants:
    def test_manifest_compilation_preserves_accepted_evidence(
        self,
        archived_architecture_application: ArchivedArchitectureApplicationFactory,
    ) -> None:
        architecture = archived_architecture_application.create(
            7,
            "6e19987b9b38c43297098b7acc48149b5d684c055659ba460ae6a6273e6b9c30",
        )
        before = architecture.client.get(architecture.publication_url)

        compiled = architecture.client.get(architecture.manifest_url)
        after = architecture.client.get(architecture.publication_url)

        assert before.status_code == 200
        assert compiled.status_code == 200, compiled.json()
        assert after.status_code == 200
        assert after.json() == before.json()


class TestArchivedSnapshotContractHappyPaths:
    @pytest.mark.parametrize(
        ("snapshot_version", "registry_fingerprint"),
        (
            (6, "38d3ff340a880f0854042c4795db2eeab598c990ff244bfae7c4b035c48e3a1b"),
            (7, "6e19987b9b38c43297098b7acc48149b5d684c055659ba460ae6a6273e6b9c30"),
        ),
    )
    def test_compiles_supported_contracts(
        self,
        archived_architecture_application: ArchivedArchitectureApplicationFactory,
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> None:
        architecture = archived_architecture_application.create(snapshot_version, registry_fingerprint)

        response = architecture.client.get(architecture.manifest_url)

        assert response.status_code == 200, response.json()
        assert {assertion["kind"] for assertion in response.json()["units"][0]["assertions"]} == {
            "artifact",
            "classifier",
            "entity",
        }
