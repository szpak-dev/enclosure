from django.db import models

from ..core.models import ShortUUIDModel


class Project(ShortUUIDModel):
    root = models.CharField(max_length=1024, unique=True)
    architecture_root = models.CharField(max_length=1024)
    language_id = models.CharField(max_length=32)
    language_version = models.CharField(max_length=32)
    package_manager_id = models.CharField(max_length=32)
    scaffolding_id = models.CharField(max_length=22)


class ProjectArchitectureConfiguration(ShortUUIDModel):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="architecture_configuration",
    )
    boundaries_yaml = models.TextField()
    shape_yaml = models.TextField()


class ProjectRecord(ShortUUIDModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="record_bindings")
    record_id = models.CharField(max_length=22)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "record_id"),
                name="projects_project_record_unique",
            ),
        ]
