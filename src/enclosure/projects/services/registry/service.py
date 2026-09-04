from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar

from wireup import injectable

from ... import models
from ...errors import ProjectsError
from .model import (
    ArchitectureConfiguration,
    ArchitectureConfigurationContent,
    ArchitectureConfigurationDocument,
    Project,
)
from .repository import ProjectRepository


@injectable
@dataclass(frozen=True)
class RegistryService:
    repository: ProjectRepository

    MAX_CONTENT_CHARACTERS: ClassVar[int] = 1024

    def find_all(self) -> tuple[Project, ...]:
        return tuple(self._project(project) for project in self.repository.find_all())

    def get(self, project_id: str) -> Project:
        return self._project(self.repository.get(project_id))

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

    def read_architecture_configuration_content(
        self,
        project_id: str,
        configuration_id: str,
        document: ArchitectureConfigurationDocument,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ArchitectureConfigurationContent:
        configuration = self.get_architecture_configuration(project_id, configuration_id)
        if configuration.revision != expected_revision:
            raise ProjectsError("Architecture configuration changed; get it again before reading content.")
        if limit < 1 or limit > self.MAX_CONTENT_CHARACTERS:
            raise ProjectsError(
                f"Architecture configuration content limit must be between 1 and {self.MAX_CONTENT_CHARACTERS}."
            )
        content = {
            ArchitectureConfigurationDocument.BOUNDARIES: configuration.boundaries_yaml,
            ArchitectureConfigurationDocument.SHAPE: configuration.shape_yaml,
        }[document]
        if offset < 0 or offset > len(content):
            raise ProjectsError("Architecture configuration content offset is outside the document.")
        next_offset = min(offset + limit, len(content))
        return ArchitectureConfigurationContent(
            project_id=project_id,
            configuration_id=configuration_id,
            revision=configuration.revision,
            document=document,
            offset=offset,
            limit=limit,
            total_characters=len(content),
            content=content[offset:next_offset],
            has_more=next_offset < len(content),
            next_offset=next_offset,
        )

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
            title=project.title,
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
            revision=self._configuration_revision(configuration.boundaries_yaml, configuration.shape_yaml),
            boundaries_yaml=configuration.boundaries_yaml,
            shape_yaml=configuration.shape_yaml,
        )

    def _configuration_revision(self, boundaries_yaml: str, shape_yaml: str) -> str:
        content = boundaries_yaml.encode("utf-8") + b"\0" + shape_yaml.encode("utf-8")
        return sha256(content).hexdigest()
