from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from wireup import injectable

from ...core.models import DjangoRepository
from ..errors import ProjectsError
from ..models import Project, ProjectArchitectureConfiguration, ProjectRecord


@injectable
@dataclass
class ProjectRepository(DjangoRepository):
    model: type[Project] = field(default=Project, init=False)

    def get_by_root(self, root: str) -> Project:
        return self.find_all().get(root=root)

    @staticmethod
    def find_architecture_configurations(project_id: str) -> QuerySet[ProjectArchitectureConfiguration]:
        return ProjectArchitectureConfiguration.objects.filter(project_id=project_id)

    @staticmethod
    def get_architecture_configuration(
        project_id: str,
        configuration_id: str,
    ) -> ProjectArchitectureConfiguration:
        return ProjectArchitectureConfiguration.objects.select_related("project").get(
            project_id=project_id,
            pk=configuration_id,
        )

    @staticmethod
    def get_project_architecture_configuration(project_id: str) -> ProjectArchitectureConfiguration:
        return ProjectArchitectureConfiguration.objects.select_related("project").get(project_id=project_id)

    @staticmethod
    def find_record_ids(project_id: str) -> tuple[str, ...]:
        return tuple(ProjectRecord.objects.filter(project_id=project_id).values_list("record_id", flat=True))

    def register(
        self,
        project_data: Mapping[str, Any],
        boundaries_yaml: str,
        shape_yaml: str,
        record_ids: Iterable[str],
    ) -> Project:
        try:
            with transaction.atomic():
                project = self.save(**project_data)
                ProjectArchitectureConfiguration.objects.create(
                    project=project,
                    boundaries_yaml=boundaries_yaml,
                    shape_yaml=shape_yaml,
                )
                self._bind_records(project, record_ids)
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error

    def update(
        self,
        id: str,
        project_data: Mapping[str, Any],
        boundaries_yaml: str,
        shape_yaml: str,
        record_ids: Iterable[str],
    ) -> Project:
        try:
            with transaction.atomic():
                project = self.get(id)
                for attribute, value in project_data.items():
                    setattr(project, attribute, value)
                project.save()
                configuration = self.get_project_architecture_configuration(project.id)
                configuration.boundaries_yaml = boundaries_yaml
                configuration.shape_yaml = shape_yaml
                configuration.save(update_fields=("boundaries_yaml", "shape_yaml"))
                project.record_bindings.all().delete()
                self._bind_records(project, record_ids)
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error

    @staticmethod
    def _bind_records(project: Project, record_ids: Iterable[str]) -> None:
        ProjectRecord.objects.bulk_create(
            ProjectRecord(project=project, record_id=record_id) for record_id in record_ids
        )
