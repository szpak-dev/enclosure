from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ... import models
from .model import ArchitectureConfiguration, Project
from .repository import ProjectRepository


@injectable
@dataclass(frozen=True)
class RegistryService:
    repository: ProjectRepository

    def find_all(self) -> tuple[Project, ...]:
        return tuple(self._project(project) for project in self.repository.find_all())

    def get(self, project_id: str) -> Project:
        return self._project(self.repository.get(project_id))

    def get_by_root(self, root: str) -> Project:
        return self._project(self.repository.get_by_root(root))

    def find_architecture_configurations(
        self,
        project_id: str,
    ) -> tuple[ArchitectureConfiguration, ...]:
        return tuple(
            self._configuration(configuration)
            for configuration in self.repository.find_architecture_configurations(project_id)
        )

    def get_architecture_configuration(
        self,
        project_id: str,
        configuration_id: str,
    ) -> ArchitectureConfiguration:
        return self._configuration(self.repository.get_architecture_configuration(project_id, configuration_id))

    def get_current_architecture_configuration(self, project_id: str) -> ArchitectureConfiguration:
        return self._configuration(self.repository.get_current_architecture_configuration(project_id))

    def register(
        self,
        data: Mapping[str, str],
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> Project:
        return self._project(self.repository.register(data, boundaries_yaml, shape_yaml))

    def update(
        self,
        project_id: str,
        data: Mapping[str, str],
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> Project:
        return self._project(self.repository.update(project_id, data, boundaries_yaml, shape_yaml))

    def _project(self, project: models.Project) -> Project:
        return Project(
            id=project.id,
            root=project.root,
            architecture_root=project.architecture_root,
            language_id=project.language_id,
            language_version=project.language_version,
            package_manager_id=project.package_manager_id,
            scaffolding_id=project.scaffolding_id,
        )

    def _configuration(
        self,
        configuration: models.ProjectArchitectureConfiguration,
    ) -> ArchitectureConfiguration:
        return ArchitectureConfiguration(
            id=configuration.id,
            project_id=configuration.project_id,
            boundaries_yaml=configuration.boundaries_yaml,
            shape_yaml=configuration.shape_yaml,
        )
