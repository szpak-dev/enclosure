from dataclasses import dataclass

from django.db.models import QuerySet
from pydantic import JsonValue
from wireup import injectable

from ..errors import ProjectsError
from ..models import Project
from .adapters import RecordsAdapter, ScaffoldingsAdapter
from .generation import GenerationResult, GenerationService
from .reports import ReportsService
from .reports.adapters import ArchitectureAdapter
from .repository import ProjectRepository
from .stack import DiscoveredProject, StackDetector


@injectable
@dataclass(frozen=True)
class ProjectsService:
    architecture: ArchitectureAdapter
    generation: GenerationService
    records: RecordsAdapter
    scaffoldings: ScaffoldingsAdapter
    stack: StackDetector
    reports: ReportsService
    repository: ProjectRepository

    def discover_project(self, root: str) -> DiscoveredProject:
        stack = self.stack.detect(root)
        return DiscoveredProject(root=root, stack=stack)

    def find_all_projects(self) -> QuerySet[Project]:
        return self.repository.find_all()

    def get_project(self, project_id: str) -> Project:
        return self.repository.get(project_id)

    def generate_source(
        self,
        project_id: str,
        destination: str,
        parameters: dict[str, JsonValue],
    ) -> GenerationResult:
        return self.generation.generate(project_id, destination, parameters)

    def register_project(
        self,
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
        record_ids: list[str],
    ) -> Project:
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id, record_ids)
        return self.repository.register(
            self._project_data(
                discovery,
                architecture_root,
                boundaries_yaml,
                shape_yaml,
                scaffolding_id,
            ),
            record_ids,
        )

    def update_project(
        self,
        project_id: str,
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
        record_ids: list[str],
    ) -> Project:
        self._validate_project(boundaries_yaml, shape_yaml, scaffolding_id, record_ids)
        return self.repository.update(
            project_id,
            self._project_data(
                discovery,
                architecture_root,
                boundaries_yaml,
                shape_yaml,
                scaffolding_id,
            ),
            record_ids,
        )

    def check_health(self, project_id: str):
        project = self.repository.get(project_id)
        return self.reports.generate_health_report(
            project.architecture_root,
            project.language_id,
            project.boundaries_yaml,
            project.shape_yaml,
        )

    def read_insights(self, project_id: str):
        project = self.repository.get(project_id)
        return self.reports.generate_insights_report(
            project.architecture_root,
            project.language_id,
            project.boundaries_yaml,
            project.shape_yaml,
        )

    def _validate_project(
        self,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
        record_ids: list[str],
    ) -> None:
        if len(record_ids) != len(set(record_ids)):
            raise ProjectsError("A project cannot bind the same record more than once.")

        self.records.check_records_existence(record_ids)
        self.scaffoldings.check_scaffolding_existence(scaffolding_id)
        self.architecture.validate_yaml_config(boundaries_yaml, shape_yaml)

    @staticmethod
    def _project_data(
        discovery: DiscoveredProject,
        architecture_root: str,
        boundaries_yaml: str,
        shape_yaml: str,
        scaffolding_id: str,
    ) -> dict[str, str]:
        return {
            "root": discovery.root,
            "architecture_root": architecture_root,
            "language_id": discovery.stack.language,
            "language_version": discovery.stack.language_version,
            "package_manager_id": discovery.stack.package_manager,
            "boundaries_yaml": boundaries_yaml,
            "shape_yaml": shape_yaml,
            "scaffolding_id": scaffolding_id,
        }
