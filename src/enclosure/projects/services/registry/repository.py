from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ....core.models import DjangoRepository
from ... import models
from .model import ProjectCandidate


@injectable
@dataclass
class ProjectRepository(DjangoRepository):
    model: type[models.Project] = field(default=models.Project, init=False)

    def find_page(self, offset: int, limit: int) -> QuerySet[models.Project]:
        return self.find_all().order_by("id")[offset : offset + limit + 1]

    def find_architecture_configurations(
        self,
        project_id: str,
    ) -> QuerySet[models.ProjectArchitectureConfiguration]:
        return models.ProjectArchitectureConfiguration.objects.filter(project_id=project_id).order_by("id")

    def find_architecture_configuration_page(
        self,
        project_id: str,
        offset: int,
        limit: int,
    ) -> QuerySet[models.ProjectArchitectureConfiguration]:
        return self.find_architecture_configurations(project_id)[offset : offset + limit + 1]

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
        candidate: ProjectCandidate,
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> models.Project:
        with transaction.atomic():
            project = self.model.objects.create(
                title=candidate.title,
                language_id=candidate.language_id,
                language_version=candidate.language_version,
                package_manager_id=candidate.package_manager_id,
                scaffolding_id=candidate.scaffolding_id,
            )
            models.ProjectArchitectureConfiguration.objects.create(
                project=project,
                boundaries_yaml=boundaries_yaml,
                shape_yaml=shape_yaml,
            )
            return project

    def update(
        self,
        project_id: str,
        candidate: ProjectCandidate,
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> models.Project:
        with transaction.atomic():
            project = self.get(project_id)
            project.title = candidate.title
            project.language_id = candidate.language_id
            project.language_version = candidate.language_version
            project.package_manager_id = candidate.package_manager_id
            project.scaffolding_id = candidate.scaffolding_id
            project.save(
                update_fields=(
                    "title",
                    "language_id",
                    "language_version",
                    "package_manager_id",
                    "scaffolding_id",
                )
            )
            configuration = self.get_current_architecture_configuration(project.id)
            configuration.boundaries_yaml = boundaries_yaml
            configuration.shape_yaml = shape_yaml
            configuration.save(update_fields=("boundaries_yaml", "shape_yaml"))
            return project
