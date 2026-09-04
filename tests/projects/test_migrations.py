import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client


@pytest.mark.django_db(transaction=True)
class TestOperatingContractMigration:
    migrate_from = [("projects", "0002_project_architecture_configuration")]
    migrate_to = [("projects", "0006_workspace_binding")]

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


@pytest.mark.django_db(transaction=True)
class TestWorkspaceBindingMigration:
    migrate_from = [("projects", "0005_guidancerelationship")]
    migrate_to = [("projects", "0006_workspace_binding")]

    def test_existing_project_keeps_its_identity_and_gains_a_named_workspace(self) -> None:
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(self.migrate_from)
            old_apps = executor.loader.project_state(self.migrate_from).apps
            project_model = old_apps.get_model("projects", "Project")
            configuration_model = old_apps.get_model("projects", "ProjectArchitectureConfiguration")
            project = project_model.objects.create(
                root="/example/migrated-project",
                architecture_root="/example/migrated-project/src",
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

            MigrationExecutor(connection).migrate(self.migrate_to)

            migrated_project = Client().get(f"/api/projects/{project.id}")
            workspaces = Client().get(f"/api/projects/{project.id}/workspaces")

            assert migrated_project.status_code == 200
            assert migrated_project.json() == {
                "id": project.id,
                "title": "migrated-project",
                "language_id": "python",
                "language_version": "3.14",
                "package_manager_id": "uv",
                "scaffolding_id": "example-scaffolding",
            }
            assert workspaces.status_code == 200
            assert workspaces.json() == [
                {
                    "id": workspaces.json()[0]["id"],
                    "project_id": project.id,
                    "root": "/example/migrated-project",
                    "architecture_root": "/example/migrated-project/src",
                    "revision": 1,
                }
            ]
        finally:
            MigrationExecutor(connection).migrate(self.migrate_to)
