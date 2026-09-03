from collections.abc import Mapping
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from wireup import injectable

from ....core.models import DjangoRepository
from ... import models
from ...errors import ProjectsError


@injectable
@dataclass
class ProjectRepository(DjangoRepository):
    model: type[models.Project] = field(default=models.Project, init=False)

    def get_by_root(self, root: str) -> models.Project:
        return self.find_all().get(root=root)

    def find_architecture_configurations(
        self,
        project_id: str,
    ) -> QuerySet[models.ProjectArchitectureConfiguration]:
        return models.ProjectArchitectureConfiguration.objects.filter(project_id=project_id)

    def get_architecture_configuration(
        self,
        project_id: str,
        configuration_id: str,
    ) -> models.ProjectArchitectureConfiguration:
        return models.ProjectArchitectureConfiguration.objects.get(
            project_id=project_id,
            pk=configuration_id,
        )

    def get_current_architecture_configuration(
        self,
        project_id: str,
    ) -> models.ProjectArchitectureConfiguration:
        return models.ProjectArchitectureConfiguration.objects.get(project_id=project_id)

    def register(
        self,
        data: Mapping[str, str],
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> models.Project:
        try:
            with transaction.atomic():
                project = self.save(**data)
                models.ProjectArchitectureConfiguration.objects.create(
                    project=project,
                    boundaries_yaml=boundaries_yaml,
                    shape_yaml=shape_yaml,
                )
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error

    def update(
        self,
        project_id: str,
        data: Mapping[str, str],
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> models.Project:
        try:
            with transaction.atomic():
                project = self.get(project_id)
                for attribute, value in data.items():
                    setattr(project, attribute, value)
                project.save()
                configuration = self.get_current_architecture_configuration(project.id)
                configuration.boundaries_yaml = boundaries_yaml
                configuration.shape_yaml = shape_yaml
                configuration.save(update_fields=("boundaries_yaml", "shape_yaml"))
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error
