from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Status
from ninja_extra import ControllerBase, api_controller, route

from ..services import ProjectsService
from . import schemas


@api_controller("/projects", tags=["Projects"])
class ProjectsController(ControllerBase):
    @route.post(
        "/discoveries",
        response=schemas.DiscoveredProject,
        operation_id="discover_project",
        summary="Discover a project",
        description="Detect the language and package manager used by a project directory.",
    )
    def discover(self, request, body: schemas.DiscoverProject):
        return DjangoRequest.resolve(request, ProjectsService).discover_project(body.root)

    @route.get(
        "",
        response=list[schemas.Project],
        operation_id="find_projects",
        summary="List projects",
        description="Return all registered projects.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, ProjectsService).find_all_projects()

    @route.post(
        "",
        response={201: schemas.Project},
        operation_id="register_project",
        summary="Register a project",
        description="Register a discovered project with its architecture configuration and supporting records.",
    )
    def register(self, request, body: schemas.RegisterProject):
        project = DjangoRequest.resolve(request, ProjectsService).register_project(
            body.discovery,
            body.architecture_root,
            body.boundaries_yaml,
            body.shape_yaml,
            body.scaffolding_id,
            body.record_ids,
        )
        return Status(201, project)

    @route.get(
        "/{project_id}",
        response=schemas.Project,
        operation_id="get_project",
        summary="Get a project",
        description="Return a registered project.",
    )
    def get(self, request, project_id: Annotated[str, Path(description="Project identifier.")]):
        return DjangoRequest.resolve(request, ProjectsService).get_project(project_id)

    @route.put(
        "/{project_id}",
        response=schemas.Project,
        operation_id="update_project",
        summary="Update a project",
        description="Replace a project's discovery data, architecture configuration, and supporting records.",
    )
    def update(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.RegisterProject,
    ):
        return DjangoRequest.resolve(request, ProjectsService).update_project(
            project_id,
            body.discovery,
            body.architecture_root,
            body.boundaries_yaml,
            body.shape_yaml,
            body.scaffolding_id,
            body.record_ids,
        )

    @route.get(
        "/{project_id}/health",
        response=schemas.HealthReport,
        operation_id="check_project_health",
        summary="Check project health",
        description="Evaluate gating architecture rules for a registered project.",
    )
    def check_health(self, request, project_id: Annotated[str, Path(description="Project identifier.")]):
        return DjangoRequest.resolve(request, ProjectsService).check_health(project_id)

    @route.get(
        "/{project_id}/insights",
        response=schemas.InsightsReport,
        operation_id="read_project_insights",
        summary="Read project insights",
        description="Evaluate non-gating architecture rules for a registered project.",
    )
    def read_insights(self, request, project_id: Annotated[str, Path(description="Project identifier.")]):
        return DjangoRequest.resolve(request, ProjectsService).read_insights(project_id)
