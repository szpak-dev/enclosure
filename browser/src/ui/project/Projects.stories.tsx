import type { Meta, StoryObj } from "@storybook/react-vite";
import { Entity, type Target } from "@siren-js/client";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { SirenResponseError } from "../../client/SirenClient";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import {
  OBJECT_CONTROL,
  STRUCTURED_FORM_EXTENSION,
} from "../siren/SirenActionForm";
import type { SirenEntityProps } from "../siren/SirenEntity";
import {
  ArchitectureConfigurationCollection,
  ArchitectureConfigurationEntity,
} from "./ArchitectureConfiguration";
import {
  GuidanceRelationshipCollection,
  GuidanceScopeCollection,
} from "./GuidanceCollections";
import { ProjectArtifactEntity } from "./ProjectArtifactEntity";
import { ProjectCollection } from "./ProjectCollection";
import { ProjectEntity } from "./ProjectEntity";
import { WorkspaceCollection } from "./WorkspaceCollection";
import { WorkspaceEntity } from "./WorkspaceEntity";

function targetHref(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);

const projectItem = sirenFixtures.embeddedEntity(
  ["project"],
  ["item"],
  "Example service",
  { id: "project-1", title: "Example service" },
  [sirenFixtures.link("/siren/projects/project-1", ["item"], "Project")],
);
const registerProject = sirenFixtures.action(
  "register_project",
  "Register a project",
  "/siren/projects",
  "POST",
  [],
);
const projects = sirenFixtures.entity(
  ["collection", "project"],
  "Projects",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [projectItem],
  [registerProject],
);
const emptyProjects = sirenFixtures.entity(
  ["collection", "project"],
  "Projects",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [registerProject],
);

const architectureItem = sirenFixtures.embeddedEntity(
  ["architecture-configuration"],
  ["item"],
  "Project architecture configuration",
  { id: "configuration-1", project_id: "project-1", revision: "revision-1" },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/architecture-configurations/configuration-1",
      ["item"],
      "ProjectArchitectureConfiguration",
    ),
  ],
);
const architectureCollection = sirenFixtures.entity(
  ["collection", "architecture-configuration"],
  "Architecture configurations",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [architectureItem],
  [],
);
const architectureConfiguration = sirenFixtures.entity(
  ["architecture-configuration"],
  "Project architecture configuration",
  {
    boundaries_total_characters: 35,
    boundaries_yaml: "boundaries:\n  tags:\n    - name: app\n",
    id: "configuration-1",
    project_id: "project-1",
    revision: "revision-1",
    shape_total_characters: 43,
    shape_yaml: "shape:\n  realms:\n    - name: application\n",
  },
  [],
  [],
  [],
);
const updateProject = sirenFixtures.action(
  "update_project",
  "Update a project",
  "/siren/projects/project-1",
  "PUT",
  [
    sirenFixtures.field("title", "Title", "text"),
    sirenFixtures.field("boundaries_yaml", "Boundaries YAML", "text"),
    sirenFixtures.field("shape_yaml", "Shape YAML", "text"),
    sirenFixtures.field("scaffolding_id", "Scaffolding ID", "text"),
  ],
);
Object.assign(updateProject, {
  [STRUCTURED_FORM_EXTENSION]: {
    controls: [
      {
        control: OBJECT_CONTROL,
        location: "body",
        mediaType: "application/json",
        name: "stack",
        required: true,
        schema: {
          additionalProperties: false,
          properties: {
            language: { title: "Language", type: "string" },
            language_version: { title: "Language version", type: "string" },
            package_manager: { title: "Package manager", type: "string" },
          },
          required: ["language", "language_version", "package_manager"],
          title: "Detected stack",
          type: "object",
        },
      },
    ],
    version: "1",
  },
});
const project = sirenFixtures.entity(
  ["project"],
  "Example service",
  {
    id: "project-1",
    language_id: "python",
    language_version: "",
    package_manager_id: "uv",
    scaffolding_id: "scaffolding-1",
    title: "Example service",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces",
      ["collection"],
      "WorkspaceBinding",
    ),
    sirenFixtures.link(
      "/siren/projects/project-1/architecture-configurations",
      ["collection"],
      "ProjectArchitectureConfiguration",
    ),
    sirenFixtures.link(
      "/siren/projects/project-1/guidance-scopes",
      ["collection"],
      "GuidanceScope",
    ),
  ],
  [],
  [updateProject],
);

const workspaceItem = sirenFixtures.embeddedEntity(
  ["workspace"],
  ["item"],
  "Workspace binding",
  {
    architecture_root: "/workspace",
    id: "workspace-1",
    project_id: "project-1",
    revision: 4,
    root: "/workspace",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces/workspace-1",
      ["item"],
      "WorkspaceBinding",
    ),
  ],
);
const workspaces = sirenFixtures.entity(
  ["collection", "workspace"],
  "Workspaces",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [workspaceItem],
  [],
);
const emptyWorkspaces = sirenFixtures.entity(
  ["collection", "workspace"],
  "Workspaces",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [],
);
const checkHealth = sirenFixtures.action(
  "check_project_health",
  "Check project health",
  "/siren/projects/project-1/workspaces/workspace-1/health-violations",
  "GET",
  [],
);
const replaceWorkspace = sirenFixtures.action(
  "replace_workspace",
  "Replace a workspace binding",
  "/siren/projects/project-1/workspaces/workspace-1",
  "PUT",
  [
    sirenFixtures.field("root", "Root", "text"),
    sirenFixtures.field("architecture_root", "Architecture root", "text"),
    sirenFixtures.field("expected_revision", "Expected revision", "number"),
  ],
);
const deleteWorkspace = sirenFixtures.action(
  "delete_workspace",
  "Delete a workspace binding",
  "/siren/projects/project-1/workspaces/workspace-1",
  "DELETE",
  [sirenFixtures.field("expected_revision", "Expected revision", "number")],
);
const workspace = sirenFixtures.entity(
  ["workspace"],
  "Workspace binding",
  workspaceItem.properties,
  [],
  [],
  [checkHealth, replaceWorkspace, deleteWorkspace],
);
const health = sirenFixtures.entity(
  ["command-result"],
  "Project health",
  {
    advisory_count: 1,
    failure_count: 0,
    healthy: true,
    revision: "health-revision-1",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces/workspace-1/health-attestation?expected_revision=health-revision-1",
      ["item"],
      "Architecture conformance attestation",
    ),
  ],
  [],
  [],
);

const record = (id: string, title: string) =>
  sirenFixtures.entity(["record"], title, { id, title }, [], [], []);
const scopeItem = sirenFixtures.embeddedEntity(
  ["guidance-scope"],
  ["item"],
  "Guidance scope",
  {
    id: "scope-1",
    position: 1,
    project_id: "project-1",
    record_id: "record-1",
  },
  [sirenFixtures.link("/siren/records/record-1", ["item"], "Record")],
);
const guidanceScopes = sirenFixtures.entity(
  ["collection", "guidance-scope"],
  "Guidance scopes",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [scopeItem],
  [],
);
const relationshipItem = sirenFixtures.embeddedEntity(
  ["guidance-relationship"],
  ["item"],
  "Guidance relationship",
  {
    id: "relationship-1",
    kind: "containment",
    project_id: "project-1",
    source_record_id: "record-1",
    target_record_id: "record-2",
  },
  [
    sirenFixtures.link("/siren/records/record-1", ["item"], "Record"),
    sirenFixtures.link("/siren/records/record-2", ["item"], "Record"),
  ],
);
const guidanceRelationships = sirenFixtures.entity(
  ["collection", "guidance-relationship"],
  "Guidance relationships",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [relationshipItem],
  [],
);

const operatingContract = sirenFixtures.entity(
  ["operating-contract"],
  "Example operating contract",
  {
    authority: "example:contract",
    id: "contract-1",
    provenance: "storybook",
    title: "Example operating contract",
  },
  [],
  [],
  [],
);

const meta = {
  component: ProjectCollection,
  args: {
    entity: projects,
    onFollow: fn(),
    onLoad: fn(async () => architectureConfiguration),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Projects/Project collection",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<SirenEntityProps>;

export const PopulatedProjects: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("link", { name: "Open project" }));
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/projects/project-1" }),
    );
  },
};

export const EmptyProjects: Story = {
  args: { entity: emptyProjects },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No projects yet",
    );
  },
};

export const NarrowProjects: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { name: "Projects" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("button", { name: "Register a project" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: "Open project" }),
    ).toBeVisible();
  },
};

export const ProjectRegistrationSuccess: Story = {
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({
        entity: project,
        kind: "entity",
      }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Register a project" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Register a project",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Register a project" }),
    );
    await expect(await within(dialog).findByRole("status")).toHaveTextContent(
      "Action completed",
    );
  },
};

export const ProjectRegistrationFailure: Story = {
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => {
        throw new SirenResponseError(
          422,
          "/siren/projects",
          "Architecture root is required.",
        );
      });
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Register a project" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Register a project",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Register a project" }),
    );
    await expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Architecture root is required.",
    );
  },
};

export const ProjectDetail: Story = {
  args: {
    entity: project,
    onLoad: fn(async (target: Target) =>
      targetHref(target).endsWith("architecture-configurations")
        ? architectureCollection
        : architectureConfiguration,
    ),
  },
  render: (args) => <ProjectEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Not reported")).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Update a project" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: /Workspaces/ }),
    ).toBeVisible();
  },
};

export const PopulatedWorkspaces: Story = {
  args: { entity: workspaces },
  render: (args) => <WorkspaceCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByText("/workspace")[0]).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Open" })).toBeVisible();
  },
};

export const EmptyWorkspaces: Story = {
  args: { entity: emptyWorkspaces },
  render: (args) => <WorkspaceCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No workspaces bound",
    );
  },
};

export const WorkspaceHealthSuccess: Story = {
  args: { entity: workspace },
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({
        entity: health,
        kind: "entity",
      }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Check project health" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Check project health",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Check project health" }),
    );
    await expect(await within(dialog).findByRole("status")).toHaveTextContent(
      "Action completed",
    );
    await expect(within(dialog).getByText("health-revision-1")).toBeVisible();
  },
};

export const WorkspaceConflict: Story = {
  args: { entity: workspace },
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => {
        throw new SirenResponseError(
          409,
          "/siren/projects/project-1/workspaces/workspace-1",
          "The workspace changed before submission.",
        );
      });
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: "More actions" }));
    await userEvent.click(
      await page.findByRole("menuitem", {
        name: "Replace a workspace binding",
      }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Replace a workspace binding",
    });
    await userEvent.click(
      within(dialog).getByRole("button", {
        name: "Replace a workspace binding",
      }),
    );
    await expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "The workspace changed before submission.",
    );
  },
};

export const WorkspaceDeleteConfirmation: Story = {
  args: { entity: workspace },
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Delete a workspace binding" }),
    );
    const confirmation = await page.findByRole("dialog", {
      name: "Delete a workspace binding?",
    });
    await expect(
      within(confirmation).getByText(/remove project configuration/),
    ).toBeVisible();
    await userEvent.click(
      within(confirmation).getByRole("button", { name: "Cancel" }),
    );
    await waitFor(() =>
      expect(
        page.queryByRole("dialog", { name: "Delete a workspace binding?" }),
      ).not.toBeInTheDocument(),
    );
  },
};

export const ArchitectureCollectionEmpty: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "architecture-configuration"],
      "Architecture configurations",
      { has_more: false, limit: 50, next_offset: 0 },
      [],
      [],
      [],
    ),
  },
  render: (args) => <ArchitectureConfigurationCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No architecture configuration",
    );
  },
};

export const ArchitectureDocuments: Story = {
  args: { entity: architectureConfiguration },
  render: (args) => <ArchitectureConfigurationEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByLabelText("boundaries YAML configuration"),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("tab", { name: "Shape" }));
    await expect(
      canvas.getByLabelText("shape YAML configuration"),
    ).toBeVisible();
  },
};

export const GuidanceResolved: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(async () => record("record-1", "Delivery guidance")),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByRole("button", {
        name: "Delivery guidance",
      }),
    ).toBeVisible();
  },
};

export const GuidanceLoading: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(() => new Promise<Entity>(() => {})),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByLabelText("Loading record record-1"),
    ).toBeVisible();
  },
};

export const GuidanceFailure: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(async () => {
      throw new Error("Record unavailable");
    }),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Record title unavailable"),
    ).toBeVisible();
  },
};

export const GuidanceRelationships: Story = {
  args: {
    entity: guidanceRelationships,
    onLoad: fn(async (target: Target) =>
      targetHref(target).endsWith("record-1")
        ? record("record-1", "Delivery lifecycle")
        : record("record-2", "Verification policy"),
    ),
  },
  render: (args) => <GuidanceRelationshipCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Containment")).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Delivery lifecycle" }),
    ).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Verification policy" }),
    ).toBeVisible();
  },
};

export const OperatingContractEvidence: Story = {
  args: { entity: operatingContract },
  render: (args) => <ProjectArtifactEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("example:contract")).toBeVisible();
    await expect(canvas.getByText("storybook")).toBeVisible();
  },
};
