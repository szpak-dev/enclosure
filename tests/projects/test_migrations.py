import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client


@pytest.mark.django_db(transaction=True)
class TestOperatingContractMigration:
    migrate_from = [("projects", "0002_project_architecture_configuration")]
    migrate_to = [("projects", "0003_operatingcontract_operatingcontractbinding_and_more")]

    def test_existing_project_becomes_explicitly_unconfigured(self) -> None:
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(self.migrate_from)
            old_apps = executor.loader.project_state(self.migrate_from).apps
            project_model = old_apps.get_model("projects", "Project")
            configuration_model = old_apps.get_model(
                "projects",
                "ProjectArchitectureConfiguration",
            )
            binding_model = old_apps.get_model("projects", "ProjectRecord")
            project = project_model.objects.create(
                root="/example/migrated-project",
                architecture_root="/example/migrated-project",
                language_id="python",
                language_version="3.14",
                package_manager_id="uv",
                scaffolding_id="example-scaffolding",
            )
            configuration_model.objects.create(
                project_id=project.id,
                boundaries_yaml="boundaries: {}\n",
                shape_yaml="shape: {}\n",
            )
            binding_model.objects.create(
                project_id=project.id,
                record_id="example-record",
            )

            MigrationExecutor(connection).migrate(self.migrate_to)

            response = Client().get(f"/api/projects/{project.id}/operating-contract-binding")

            assert response.status_code == 409
            assert response.json() == {
                "state": "unconfigured",
                "project_id": project.id,
            }
        finally:
            MigrationExecutor(connection).migrate(self.migrate_to)
