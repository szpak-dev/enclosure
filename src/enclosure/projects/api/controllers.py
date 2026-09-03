from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Status
from ninja_extra import ControllerBase, api_controller, route

from ..services import ProjectsService
from . import schemas


@api_controller("/projects", tags=["Projects"])
class ProjectsController(ControllerBase):
    @route.post(
        "/operating-contracts",
        response={201: schemas.OperatingContract},
        operation_id="create_operating_contract",
        summary="Create an operating contract",
        description="Create an operating-contract envelope with one canonical authority and provenance.",
    )
    def create_operating_contract(self, request, body: schemas.CreateOperatingContract):
        contract = DjangoRequest.resolve(request, ProjectsService).create_operating_contract(
            body.title,
            body.authority,
            body.provenance,
        )
        return Status(201, contract)

    @route.get(
        "/operating-contracts/{contract_id}",
        response=schemas.OperatingContract,
        operation_id="get_operating_contract",
        summary="Get an operating contract",
        description="Return an operating-contract envelope and its canonical authority.",
    )
    def get_operating_contract(
        self,
        request,
        contract_id: Annotated[str, Path(description="Operating-contract identifier.")],
    ):
        return DjangoRequest.resolve(request, ProjectsService).get_operating_contract(contract_id)

    @route.post(
        "/operating-contracts/{contract_id}/revisions",
        response={201: schemas.OperatingContractRevision},
        operation_id="publish_operating_contract_revision",
        summary="Publish an operating-contract revision",
        description="Validate and publish the next immutable revision of an operating contract.",
    )
    def publish_operating_contract_revision(
        self,
        request,
        contract_id: Annotated[str, Path(description="Operating-contract identifier.")],
        body: schemas.PublishOperatingContractRevision,
    ):
        references = tuple(reference.model_dump(mode="python") for reference in body.references)
        revision = DjangoRequest.resolve(request, ProjectsService).publish_operating_contract_revision(
            contract_id,
            tuple(body.record_ids),
            references,
        )
        return Status(201, revision)

    @route.get(
        "/operating-contracts/{contract_id}/revisions/{version}",
        response=schemas.OperatingContractRevision,
        operation_id="get_operating_contract_revision",
        summary="Get an operating-contract revision",
        description="Return one immutable published operating-contract revision.",
    )
    def get_operating_contract_revision(
        self,
        request,
        contract_id: Annotated[str, Path(description="Operating-contract identifier.")],
        version: Annotated[int, Path(description="Contract-local revision number.")],
    ):
        return DjangoRequest.resolve(request, ProjectsService).get_operating_contract_revision(contract_id, version)

    @route.post(
        "/workspace-contexts",
        response=schemas.WorkspaceContext,
        operation_id="get_workspace_context",
        summary="Get workspace context",
        description="Resolve a registered workspace and return compact task-relevant linked guidance.",
    )
    def workspace_context(self, request, body: schemas.GetWorkspaceContext):
        return DjangoRequest.resolve(request, ProjectsService).get_workspace_context(body.root, body.task)

    @route.get(
        "/{project_id}/guidance-scopes",
        response=list[schemas.GuidanceScope],
        operation_id="find_guidance_scopes",
        summary="List guidance scopes",
        description="Return the ordered optional guidance records eligible for this project.",
    )
    def find_guidance_scopes(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
    ):
        return list(DjangoRequest.resolve(request, ProjectsService).find_guidance_scopes(project_id))

    @route.put(
        "/{project_id}/guidance-scopes",
        response=list[schemas.GuidanceScope],
        operation_id="replace_guidance_scopes",
        summary="Replace guidance scopes",
        description="Replace the project's ordered allow-list of optional guidance records.",
    )
    def replace_guidance_scopes(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.ReplaceGuidanceScopes,
    ):
        return list(
            DjangoRequest.resolve(request, ProjectsService).replace_guidance_scopes(
                project_id,
                tuple(body.record_ids),
            )
        )

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
        response=list[schemas.ProjectReference],
        operation_id="find_projects",
        summary="List projects",
        description="Return references to all registered projects.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, ProjectsService).find_all_projects()

    @route.post(
        "/root-search-results",
        response=schemas.ProjectReference,
        operation_id="find_project_by_root",
        summary="Find a project by root",
        description="Find a registered project by its exact root path.",
    )
    def find_by_root(self, request, body: schemas.FindProjectByRoot):
        return DjangoRequest.resolve(request, ProjectsService).find_project_by_root(body.root)

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

    @route.post(
        "/{project_id}/operating-contract-bindings",
        response={201: schemas.ConfiguredOperatingContractBinding},
        operation_id="bind_project_operating_contract",
        summary="Bind a project operating contract",
        description="Create the single active operating-contract binding for an unconfigured project.",
    )
    def bind_operating_contract(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.WriteOperatingContractBinding,
    ):
        binding = DjangoRequest.resolve(request, ProjectsService).bind_project_operating_contract(
            project_id,
            body.contract_id,
            body.version,
            body.update_policy,
        )
        return Status(201, binding)

    @route.get(
        "/{project_id}/operating-contract-binding",
        response={
            200: schemas.ConfiguredOperatingContractBinding,
            409: schemas.UnconfiguredOperatingContractBinding,
        },
        operation_id="get_project_operating_contract_binding",
        summary="Get a project operating-contract binding",
        description="Return the configured binding and effective revision, or an explicit unconfigured state.",
    )
    def get_operating_contract_binding(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
    ):
        binding = DjangoRequest.resolve(request, ProjectsService).get_project_operating_contract_binding(project_id)
        if binding.state == "unconfigured":
            return Status(409, binding)
        return binding

    @route.put(
        "/{project_id}/operating-contract-binding",
        response=schemas.ConfiguredOperatingContractBinding,
        operation_id="replace_project_operating_contract_binding",
        summary="Replace a project operating-contract binding",
        description="Explicitly replace the active contract revision and update policy.",
    )
    def replace_operating_contract_binding(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.WriteOperatingContractBinding,
    ):
        return DjangoRequest.resolve(request, ProjectsService).replace_project_operating_contract_binding(
            project_id,
            body.contract_id,
            body.version,
            body.update_policy,
        )

    @route.post(
        "/{project_id}/source-generations",
        response=schemas.GeneratedProjectSource,
        operation_id="generate_project_source",
        summary="Generate project source",
        description="Render the project's associated scaffolding into a project-relative destination.",
    )
    def generate_source(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.GenerateProjectSource,
    ):
        return DjangoRequest.resolve(request, ProjectsService).generate_source(
            project_id,
            body.destination,
            body.parameters,
        )

    @route.get(
        "/{project_id}/architecture-configurations",
        response=list[schemas.ProjectArchitectureConfigurationReference],
        operation_id="find_project_architecture_configurations",
        summary="List project architecture configurations",
        description="Return compact references to a project's architecture configurations.",
    )
    def find_architecture_configurations(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
    ):
        return DjangoRequest.resolve(request, ProjectsService).find_project_architecture_configurations(project_id)

    @route.get(
        "/{project_id}/architecture-configurations/{configuration_id}",
        response=schemas.ProjectArchitectureConfiguration,
        operation_id="get_project_architecture_configuration",
        summary="Get project architecture configuration",
        description="Return one project's Modwire boundary and architecture-shape configuration.",
    )
    def get_architecture_configuration(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        configuration_id: Annotated[str, Path(description="Architecture configuration identifier.")],
    ):
        return DjangoRequest.resolve(request, ProjectsService).get_project_architecture_configuration(
            project_id,
            configuration_id,
        )

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
        description="Replace a project's discovery data and architecture configuration.",
    )
    def update(
        self,
        request,
        project_id: Annotated[str, Path(description="Project identifier.")],
        body: schemas.UpdateProject,
    ):
        return DjangoRequest.resolve(request, ProjectsService).update_project(
            project_id,
            body.discovery,
            body.architecture_root,
            body.boundaries_yaml,
            body.shape_yaml,
            body.scaffolding_id,
        )

    @route.get(
        "/{project_id}/health-violations",
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
