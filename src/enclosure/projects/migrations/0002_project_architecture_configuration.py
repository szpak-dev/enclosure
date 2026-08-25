import django.db.models.deletion
import shortuuid.django_fields
from django.db import migrations, models


def move_configuration_to_child_resource(apps, schema_editor) -> None:
    Project = apps.get_model("projects", "Project")
    ProjectArchitectureConfiguration = apps.get_model("projects", "ProjectArchitectureConfiguration")
    ProjectArchitectureConfiguration.objects.bulk_create(
        [
            ProjectArchitectureConfiguration(
                project_id=project.id,
                boundaries_yaml=project.boundaries_yaml,
                shape_yaml=project.shape_yaml,
            )
            for project in Project.objects.iterator()
        ]
    )


def restore_configuration_to_project(apps, schema_editor) -> None:
    Project = apps.get_model("projects", "Project")
    ProjectArchitectureConfiguration = apps.get_model("projects", "ProjectArchitectureConfiguration")
    for configuration in ProjectArchitectureConfiguration.objects.iterator():
        Project.objects.filter(pk=configuration.project_id).update(
            boundaries_yaml=configuration.boundaries_yaml,
            shape_yaml=configuration.shape_yaml,
        )


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProjectArchitectureConfiguration",
            fields=[
                (
                    "id",
                    shortuuid.django_fields.ShortUUIDField(
                        alphabet=None,
                        editable=False,
                        length=22,
                        max_length=22,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("boundaries_yaml", models.TextField()),
                ("shape_yaml", models.TextField()),
                (
                    "project",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="architecture_configuration",
                        to="projects.project",
                    ),
                ),
            ],
        ),
        migrations.RunPython(move_configuration_to_child_resource, restore_configuration_to_project),
        migrations.RemoveField(model_name="project", name="boundaries_yaml"),
        migrations.RemoveField(model_name="project", name="shape_yaml"),
    ]
